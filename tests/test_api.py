"""Tests for the async PetSafe API client."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientSession

from custom_components.petsafe_smartfeed.api import (
    PetSafeAuthError,
    PetSafeClient,
    PetSafeError,
    PetSafeFeederData,
)
from custom_components.petsafe_smartfeed.const import (
    COGNITO_ENDPOINT,
    API_BASE_URL,
)

from conftest import (
    MOCK_COGNITO_AUTH_RESULT,
    MOCK_COGNITO_INITIATE_AUTH_RESPONSE,
    MOCK_COGNITO_REFRESH_RESULT,
    MOCK_FEEDER_API_RESPONSE,
    MOCK_FEEDER_LOW_BATTERY,
)


def _make_response(status: int, json_data: dict):
    """Create a mock aiohttp response context manager."""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data)
    resp.reason = "OK" if status == 200 else "Error"
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=resp)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


class TestPetSafeFeederData:
    """Test PetSafeFeederData parsing."""

    def test_from_api_normal(self):
        data = PetSafeFeederData.from_api(MOCK_FEEDER_API_RESPONSE)
        assert data.thing_name == "smart_feed_abc123"
        assert data.friendly_name == "Kitchen Feeder"
        assert data.food_low_status == 0
        assert data.food_low_label == "Full"
        assert data.slow_feed is False
        assert data.paused is False
        assert data.child_lock is False
        assert data.is_batteries_installed is True
        assert data.network_rssi == -48
        assert data.firmware_version == "V2.0.9"
        # Battery: (26000 - 22755) / (29100 - 22755) * 100 ≈ 51%
        assert 40 <= data.battery_level <= 60

    def test_from_api_low_battery(self):
        data = PetSafeFeederData.from_api(MOCK_FEEDER_LOW_BATTERY)
        assert data.food_low_status == 1
        assert data.food_low_label == "Low"
        # Battery: (23000 - 22755) / (29100 - 22755) * 100 ≈ 3.9%
        assert data.battery_level < 10

    def test_from_api_no_batteries(self):
        no_bat = {**MOCK_FEEDER_API_RESPONSE, "is_batteries_installed": False}
        data = PetSafeFeederData.from_api(no_bat)
        assert data.battery_level == 0

    def test_from_api_empty_food(self):
        empty = {**MOCK_FEEDER_API_RESPONSE, "is_food_low": 2}
        data = PetSafeFeederData.from_api(empty)
        assert data.food_low_label == "Empty"

    def test_battery_clamp_low(self):
        low = {**MOCK_FEEDER_API_RESPONSE, "battery_voltage": "20000"}
        data = PetSafeFeederData.from_api(low)
        assert data.battery_level == 0

    def test_battery_clamp_high(self):
        high = {**MOCK_FEEDER_API_RESPONSE, "battery_voltage": "32000"}
        data = PetSafeFeederData.from_api(high)
        assert data.battery_level == 100


class TestPetSafeClientAuth:
    """Test Cognito auth flow."""

    @pytest.fixture
    def mock_session(self):
        session = MagicMock(spec=ClientSession)
        return session

    @pytest.fixture
    def client(self, mock_session):
        return PetSafeClient(session=mock_session, email="user@example.com")

    @pytest.mark.asyncio
    async def test_request_code(self, client, mock_session):
        mock_session.post = MagicMock(
            return_value=_make_response(200, MOCK_COGNITO_INITIATE_AUTH_RESPONSE)
        )

        await client.request_code()

        assert client._challenge_name == "CUSTOM_CHALLENGE"
        assert client._cognito_session == "mock-session-token"
        assert client._username == "user@example.com"

        # Verify correct Cognito endpoint was called
        mock_session.post.assert_called_once()
        call_args = mock_session.post.call_args
        assert call_args[0][0] == COGNITO_ENDPOINT

    @pytest.mark.asyncio
    async def test_request_tokens_from_code(self, client, mock_session):
        # Set up state from request_code
        client._challenge_name = "CUSTOM_CHALLENGE"
        client._cognito_session = "mock-session-token"
        client._username = "user@example.com"

        mock_session.post = MagicMock(
            return_value=_make_response(200, MOCK_COGNITO_AUTH_RESULT)
        )

        await client.request_tokens_from_code("123456")

        assert client.id_token == "mock-id-token"
        assert client.access_token == "mock-access-token"
        assert client.refresh_token == "mock-refresh-token"
        assert client.token_expires_at > time.time()

    @pytest.mark.asyncio
    async def test_request_tokens_strips_non_digits(self, client, mock_session):
        client._challenge_name = "CUSTOM_CHALLENGE"
        client._cognito_session = "mock-session-token"
        client._username = "user@example.com"

        mock_session.post = MagicMock(
            return_value=_make_response(200, MOCK_COGNITO_AUTH_RESULT)
        )

        await client.request_tokens_from_code("12-34-56")

        # Verify the code was cleaned
        call_args = mock_session.post.call_args
        # The call is via context manager, so we check the json payload
        json_payload = call_args[1]["json"]
        assert json_payload["ChallengeResponses"]["ANSWER"] == "123456"

    @pytest.mark.asyncio
    async def test_refresh_tokens(self, client, mock_session):
        client.refresh_token = "mock-refresh-token"

        mock_session.post = MagicMock(
            return_value=_make_response(200, MOCK_COGNITO_REFRESH_RESULT)
        )

        await client.refresh_tokens()

        assert client.id_token == "mock-id-token-refreshed"
        assert client.access_token == "mock-access-token-refreshed"

    @pytest.mark.asyncio
    async def test_auth_error_raises(self, client, mock_session):
        mock_session.post = MagicMock(
            return_value=_make_response(
                400,
                {
                    "__type": "NotAuthorizedException",
                    "message": "Invalid credentials",
                },
            )
        )

        with pytest.raises(PetSafeAuthError, match="Invalid credentials"):
            await client.request_code()

    @pytest.mark.asyncio
    async def test_refresh_no_token_raises(self, client, mock_session):
        client.refresh_token = None
        with pytest.raises(PetSafeAuthError, match="No refresh token"):
            await client.refresh_tokens()


class TestPetSafeClientAPI:
    """Test PetSafe REST API calls."""

    @pytest.fixture
    def client(self):
        session = MagicMock(spec=ClientSession)
        c = PetSafeClient(
            session=session,
            email="user@example.com",
            id_token="mock-id-token",
            refresh_token="mock-refresh-token",
            access_token="mock-access-token",
        )
        c.token_expires_at = time.time() + 3600  # not expired
        return c

    @pytest.mark.asyncio
    async def test_get_feeders(self, client):
        client._session.get = MagicMock(
            return_value=_make_response(200, [MOCK_FEEDER_API_RESPONSE])
        )

        feeders = await client.get_feeders()

        assert len(feeders) == 1
        assert feeders[0].thing_name == "smart_feed_abc123"
        assert feeders[0].friendly_name == "Kitchen Feeder"

    @pytest.mark.asyncio
    async def test_get_feeders_uses_correct_url(self, client):
        client._session.get = MagicMock(
            return_value=_make_response(200, [MOCK_FEEDER_API_RESPONSE])
        )

        await client.get_feeders()

        call_args = client._session.get.call_args
        assert call_args[0][0] == f"{API_BASE_URL}feeders"

    @pytest.mark.asyncio
    async def test_feed(self, client):
        client._session.post = MagicMock(
            return_value=_make_response(200, {})
        )

        await client.feed("smart_feed_abc123", amount=1, slow_feed=False)

        call_args = client._session.post.call_args
        assert "smart_feed_abc123/meals" in call_args[0][0]
        assert call_args[1]["json"] == {"amount": 1, "slow_feed": False}

    @pytest.mark.asyncio
    async def test_set_setting(self, client):
        client._session.put = MagicMock(
            return_value=_make_response(200, {})
        )

        await client.set_setting("smart_feed_abc123", "slow_feed", True)

        call_args = client._session.put.call_args
        assert "smart_feed_abc123/settings/slow_feed" in call_args[0][0]
        assert call_args[1]["json"] == {"value": True}

    @pytest.mark.asyncio
    async def test_api_401_raises_auth_error(self, client):
        client._session.get = MagicMock(
            return_value=_make_response(401, {})
        )

        with pytest.raises(PetSafeAuthError):
            await client.get_feeders()

    @pytest.mark.asyncio
    async def test_api_500_raises_error(self, client):
        resp = _make_response(500, {})
        # Override reason
        resp_inner = AsyncMock()
        resp_inner.status = 500
        resp_inner.reason = "Internal Server Error"
        resp_inner.json = AsyncMock(return_value={})
        resp.__aenter__ = AsyncMock(return_value=resp_inner)
        client._session.get = MagicMock(return_value=resp)

        with pytest.raises(PetSafeError, match="500"):
            await client.get_feeders()

    @pytest.mark.asyncio
    async def test_auto_refresh_when_expired(self, client):
        client.token_expires_at = time.time() - 10  # expired

        # First call = refresh (post to Cognito), second = post to Cognito happens
        # but we also need GET for feeders
        refresh_resp = _make_response(200, MOCK_COGNITO_REFRESH_RESULT)
        feeders_resp = _make_response(200, [MOCK_FEEDER_API_RESPONSE])

        client._session.post = MagicMock(return_value=refresh_resp)
        client._session.get = MagicMock(return_value=feeders_resp)

        feeders = await client.get_feeders()

        # Refresh should have been called
        assert client.id_token == "mock-id-token-refreshed"
        assert len(feeders) == 1

    @pytest.mark.asyncio
    async def test_no_auth_header_raises(self):
        session = MagicMock(spec=ClientSession)
        client = PetSafeClient(session=session, email="user@example.com")

        with pytest.raises(PetSafeAuthError, match="Not authenticated"):
            # Force skip token refresh by not setting token_expires_at
            client.token_expires_at = time.time() + 3600
            await client.get_feeders()
