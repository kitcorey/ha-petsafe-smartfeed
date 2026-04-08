"""Async API client for PetSafe Smart Feed."""

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import aiohttp

from .const import (
    API_BASE_URL,
    BATTERY_VOLTAGE_MAX,
    BATTERY_VOLTAGE_MIN,
    COGNITO_CLIENT_ID,
    COGNITO_ENDPOINT,
    FOOD_STATUS_MAP,
)

_LOGGER = logging.getLogger(__name__)


class PetSafeAuthError(Exception):
    """Authentication failed."""


class PetSafeError(Exception):
    """General API error."""


@dataclass
class PetSafeFeederData:
    """Parsed feeder data."""

    thing_name: str
    friendly_name: str
    battery_level: int
    food_low_status: int
    food_low_label: str
    slow_feed: bool
    paused: bool
    child_lock: bool
    is_batteries_installed: bool
    battery_voltage: int = 0
    last_seen: datetime | None = None
    revision_synced: bool = True
    revision_desired: int | None = None
    revision_reported: int | None = None
    raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_api(cls, data: dict) -> "PetSafeFeederData":
        """Create from raw API response dict."""
        settings = data.get("settings", {})
        raw_voltage = int(data.get("battery_voltage", "0"))
        is_batteries = bool(data.get("is_batteries_installed", False))

        if is_batteries and raw_voltage > 0:
            battery_pct = int(
                (raw_voltage - BATTERY_VOLTAGE_MIN)
                / (BATTERY_VOLTAGE_MAX - BATTERY_VOLTAGE_MIN)
                * 100
            )
            battery_pct = max(0, min(100, battery_pct))
        else:
            battery_pct = 0

        food_status = int(data.get("is_food_low", 0))

        # Parse connection timestamp
        last_seen = None
        ts_str = data.get("connection_status_timestamp")
        if ts_str:
            try:
                last_seen = datetime.fromisoformat(
                    ts_str.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        revision_synced = (
            data.get("revision_desired") == data.get("revision_reported")
        )

        return cls(
            thing_name=data["thing_name"],
            friendly_name=settings.get("friendly_name", data.get("thing_name", "")),
            battery_level=battery_pct,
            battery_voltage=raw_voltage,
            food_low_status=food_status,
            food_low_label=FOOD_STATUS_MAP.get(food_status, "Unknown"),
            slow_feed=bool(settings.get("slow_feed", False)),
            paused=bool(settings.get("paused", False)),
            child_lock=bool(settings.get("child_lock", False)),
            is_batteries_installed=is_batteries,
            last_seen=last_seen,
            revision_synced=revision_synced,
            revision_desired=data.get("revision_desired"),
            revision_reported=data.get("revision_reported"),
            raw=data,
        )


class PetSafeClient:
    """Async client for the PetSafe Smart Feed API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        email: str,
        id_token: str | None = None,
        refresh_token: str | None = None,
        access_token: str | None = None,
    ) -> None:
        self._session = session
        self.email = email
        self.id_token = id_token
        self.refresh_token = refresh_token
        self.access_token = access_token
        self.token_expires_at: float = 0
        self._cognito_session: str | None = None
        self._challenge_name: str | None = None
        self._username: str | None = None

    async def _cognito_request(self, target: str, payload: dict) -> dict:
        """Make a request to the AWS Cognito Identity Provider API."""
        headers = {
            "Content-Type": "application/x-amz-json-1.1",
            "X-Amz-Target": f"AWSCognitoIdentityProviderService.{target}",
        }
        try:
            async with self._session.post(
                COGNITO_ENDPOINT, headers=headers, json=payload
            ) as resp:
                body = await resp.json(content_type=None)
                if resp.status != 200:
                    error_type = body.get("__type", "UnknownError")
                    error_msg = body.get("message", resp.reason)
                    if "NotAuthorizedException" in error_type:
                        raise PetSafeAuthError(error_msg)
                    raise PetSafeError(
                        f"Cognito {target} failed: {error_type}: {error_msg}"
                    )
                return body
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise PetSafeError(f"Network error during {target}: {err}") from err

    async def request_code(self) -> None:
        """Request a login code be sent to the user's email."""
        response = await self._cognito_request(
            "InitiateAuth",
            {
                "AuthFlow": "CUSTOM_AUTH",
                "ClientId": COGNITO_CLIENT_ID,
                "AuthParameters": {
                    "USERNAME": self.email,
                    "AuthFlow": "CUSTOM_CHALLENGE",
                },
            },
        )
        self._challenge_name = response["ChallengeName"]
        self._cognito_session = response["Session"]
        self._username = response.get("ChallengeParameters", {}).get(
            "USERNAME", self.email
        )

    async def request_tokens_from_code(self, code: str) -> None:
        """Exchange the email code for auth tokens."""
        clean_code = re.sub(r"\D", "", code)
        response = await self._cognito_request(
            "RespondToAuthChallenge",
            {
                "ClientId": COGNITO_CLIENT_ID,
                "ChallengeName": self._challenge_name,
                "Session": self._cognito_session,
                "ChallengeResponses": {
                    "ANSWER": clean_code,
                    "USERNAME": self._username or self.email,
                },
            },
        )
        result = response["AuthenticationResult"]
        self.id_token = result["IdToken"]
        self.access_token = result["AccessToken"]
        self.refresh_token = result["RefreshToken"]
        self.token_expires_at = time.time() + result["ExpiresIn"]

    async def refresh_tokens(self) -> None:
        """Refresh auth tokens using the refresh token."""
        if not self.refresh_token:
            raise PetSafeAuthError("No refresh token available")
        response = await self._cognito_request(
            "InitiateAuth",
            {
                "AuthFlow": "REFRESH_TOKEN_AUTH",
                "ClientId": COGNITO_CLIENT_ID,
                "AuthParameters": {
                    "REFRESH_TOKEN": self.refresh_token,
                },
            },
        )
        if "Session" in response:
            self._cognito_session = response["Session"]
        result = response["AuthenticationResult"]
        self.id_token = result["IdToken"]
        self.access_token = result["AccessToken"]
        # Refresh flow may not return a new refresh token
        if "RefreshToken" in result:
            self.refresh_token = result["RefreshToken"]
        self.token_expires_at = time.time() + result["ExpiresIn"]

    async def _ensure_token(self) -> None:
        """Refresh the token if it's about to expire."""
        if self.id_token and time.time() >= self.token_expires_at - 60:
            await self.refresh_tokens()

    def _api_headers(self) -> dict:
        """Build headers for PetSafe API calls."""
        if not self.id_token:
            raise PetSafeAuthError("Not authenticated")
        return {
            "Content-Type": "application/json",
            "Authorization": self.id_token,
        }

    async def _api_get(self, path: str) -> dict | list:
        """GET from PetSafe API."""
        await self._ensure_token()
        try:
            async with self._session.get(
                f"{API_BASE_URL}{path}", headers=self._api_headers()
            ) as resp:
                if resp.status == 401:
                    raise PetSafeAuthError("Token expired or invalid")
                if resp.status != 200:
                    raise PetSafeError(
                        f"API GET {path} failed: {resp.status} {resp.reason}"
                    )
                return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise PetSafeError(f"Network error during GET {path}: {err}") from err

    async def _api_post(self, path: str, data: dict | None = None) -> dict | list:
        """POST to PetSafe API."""
        await self._ensure_token()
        try:
            async with self._session.post(
                f"{API_BASE_URL}{path}", headers=self._api_headers(), json=data
            ) as resp:
                if resp.status == 401:
                    raise PetSafeAuthError("Token expired or invalid")
                if resp.status not in (200, 201):
                    raise PetSafeError(
                        f"API POST {path} failed: {resp.status} {resp.reason}"
                    )
                return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise PetSafeError(f"Network error during POST {path}: {err}") from err

    async def _api_put(self, path: str, data: dict | None = None) -> dict | list:
        """PUT to PetSafe API."""
        await self._ensure_token()
        try:
            async with self._session.put(
                f"{API_BASE_URL}{path}", headers=self._api_headers(), json=data
            ) as resp:
                if resp.status == 401:
                    raise PetSafeAuthError("Token expired or invalid")
                if resp.status != 200:
                    raise PetSafeError(
                        f"API PUT {path} failed: {resp.status} {resp.reason}"
                    )
                return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise PetSafeError(f"Network error during PUT {path}: {err}") from err

    async def get_feeders(self) -> list[PetSafeFeederData]:
        """Fetch all feeders and parse into data objects."""
        raw_feeders = await self._api_get("feeders")
        return [PetSafeFeederData.from_api(f) for f in raw_feeders]

    async def get_feeder(self, thing_name: str) -> PetSafeFeederData:
        """Fetch a single feeder's data."""
        raw = await self._api_get(f"feeders/{thing_name}/")
        return PetSafeFeederData.from_api(raw)

    async def feed(
        self, thing_name: str, amount: int = 1, slow_feed: bool = False
    ) -> None:
        """Dispense food. Amount is in 1/8 cup increments (1-8)."""
        await self._api_post(
            f"feeders/{thing_name}/meals",
            data={"amount": amount, "slow_feed": slow_feed},
        )

    async def set_setting(
        self, thing_name: str, setting: str, value: bool | str
    ) -> None:
        """Update a feeder setting."""
        await self._api_put(
            f"feeders/{thing_name}/settings/{setting}",
            data={"value": value},
        )
