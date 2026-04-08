"""Config flow for PetSafe Smart Feed."""

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PetSafeAuthError, PetSafeClient, PetSafeError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_EMAIL,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class PetSafeSmartFeedConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PetSafe Smart Feed."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._client: PetSafeClient | None = None
        self._email: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Enter email address."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._email = user_input[CONF_EMAIL].strip().lower()
            await self.async_set_unique_id(self._email)
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass)
            self._client = PetSafeClient(session=session, email=self._email)

            try:
                await self._client.request_code()
            except PetSafeError as err:
                _LOGGER.error("Failed to request code: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error requesting code")
                errors["base"] = "unknown"
            else:
                return await self.async_step_code()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_EMAIL): str}),
            errors=errors,
        )

    async def async_step_code(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: Enter the code received via email."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await self._client.request_tokens_from_code(user_input["code"])
            except PetSafeAuthError:
                errors["base"] = "invalid_auth"
            except PetSafeError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during code verification")
                errors["base"] = "unknown"
            else:
                # Verify we can reach feeders
                try:
                    feeders = await self._client.get_feeders()
                except Exception:
                    _LOGGER.exception("Failed to fetch feeders after auth")
                    errors["base"] = "cannot_connect"
                else:
                    if not feeders:
                        return self.async_abort(reason="no_feeders")

                    return self.async_create_entry(
                        title=self._email,
                        data={
                            CONF_EMAIL: self._email,
                            CONF_ID_TOKEN: self._client.id_token,
                            CONF_REFRESH_TOKEN: self._client.refresh_token,
                            CONF_ACCESS_TOKEN: self._client.access_token,
                        },
                    )

        return self.async_show_form(
            step_id="code",
            data_schema=vol.Schema({vol.Required("code"): str}),
            description_placeholders={"email": self._email},
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication."""
        self._email = entry_data[CONF_EMAIL]
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1 of reauth: request a new code."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = async_get_clientsession(self.hass)
            self._client = PetSafeClient(session=session, email=self._email)
            try:
                await self._client.request_code()
            except PetSafeError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during reauth")
                errors["base"] = "unknown"
            else:
                return await self.async_step_reauth_code()

        return self.async_show_form(
            step_id="reauth_confirm",
            description_placeholders={"email": self._email},
            errors=errors,
        )

    async def async_step_reauth_code(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2 of reauth: enter the code."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await self._client.request_tokens_from_code(user_input["code"])
            except PetSafeAuthError:
                errors["base"] = "invalid_auth"
            except PetSafeError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during reauth code")
                errors["base"] = "unknown"
            else:
                entry = self.hass.config_entries.async_get_entry(
                    self.context["entry_id"]
                )
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        CONF_ID_TOKEN: self._client.id_token,
                        CONF_REFRESH_TOKEN: self._client.refresh_token,
                        CONF_ACCESS_TOKEN: self._client.access_token,
                    },
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_code",
            data_schema=vol.Schema({vol.Required("code"): str}),
            description_placeholders={"email": self._email},
            errors=errors,
        )
