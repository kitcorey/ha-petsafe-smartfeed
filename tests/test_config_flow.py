"""Tests for PetSafe Smart Feed config flow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.petsafe_smartfeed.api import (
    PetSafeAuthError,
    PetSafeClient,
    PetSafeError,
    PetSafeFeederData,
)
from custom_components.petsafe_smartfeed.config_flow import PetSafeSmartFeedConfigFlow
from custom_components.petsafe_smartfeed.const import (
    CONF_ACCESS_TOKEN,
    CONF_EMAIL,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    DOMAIN,
)

from conftest import MOCK_FEEDER_API_RESPONSE


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.config_entries = MagicMock()
    return hass


@pytest.fixture
def mock_client():
    client = MagicMock(spec=PetSafeClient)
    client.request_code = AsyncMock()
    client.request_tokens_from_code = AsyncMock()
    client.id_token = "mock-id-token"
    client.refresh_token = "mock-refresh-token"
    client.access_token = "mock-access-token"
    feeder = PetSafeFeederData.from_api(MOCK_FEEDER_API_RESPONSE)
    client.get_feeders = AsyncMock(return_value=[feeder])
    return client


class TestConfigFlow:
    """Test the config flow steps."""

    @pytest.mark.asyncio
    async def test_user_step_shows_form(self):
        flow = PetSafeSmartFeedConfigFlow()
        flow.hass = MagicMock()

        result = await flow.async_step_user(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_user_step_connect_error(self, mock_client):
        mock_client.request_code = AsyncMock(
            side_effect=PetSafeError("Connection failed")
        )

        flow = PetSafeSmartFeedConfigFlow()
        flow.hass = MagicMock()
        flow.async_set_unique_id = AsyncMock()
        flow._abort_if_unique_id_configured = MagicMock()

        with patch(
            "custom_components.petsafe_smartfeed.config_flow.async_get_clientsession"
        ), patch(
            "custom_components.petsafe_smartfeed.config_flow.PetSafeClient",
            return_value=mock_client,
        ):
            result = await flow.async_step_user(
                user_input={CONF_EMAIL: "user@example.com"}
            )

        assert result["type"] == "form"
        assert result["errors"]["base"] == "cannot_connect"

    @pytest.mark.asyncio
    async def test_code_step_invalid_code(self, mock_client):
        mock_client.request_tokens_from_code = AsyncMock(
            side_effect=PetSafeAuthError("Invalid code")
        )

        flow = PetSafeSmartFeedConfigFlow()
        flow.hass = MagicMock()
        flow._client = mock_client
        flow._email = "user@example.com"

        result = await flow.async_step_code(user_input={"code": "000000"})

        assert result["type"] == "form"
        assert result["errors"]["base"] == "invalid_auth"

    @pytest.mark.asyncio
    async def test_code_step_no_feeders(self, mock_client):
        mock_client.get_feeders = AsyncMock(return_value=[])

        flow = PetSafeSmartFeedConfigFlow()
        flow.hass = MagicMock()
        flow._client = mock_client
        flow._email = "user@example.com"

        result = await flow.async_step_code(user_input={"code": "123456"})

        assert result["type"] == "abort"
        assert result["reason"] == "no_feeders"

    @pytest.mark.asyncio
    async def test_full_flow_success(self, mock_client):
        flow = PetSafeSmartFeedConfigFlow()
        flow.hass = MagicMock()
        flow._client = mock_client
        flow._email = "user@example.com"

        result = await flow.async_step_code(user_input={"code": "123456"})

        assert result["type"] == "create_entry"
        assert result["title"] == "user@example.com"
        assert result["data"][CONF_EMAIL] == "user@example.com"
        assert result["data"][CONF_ID_TOKEN] == "mock-id-token"
        assert result["data"][CONF_REFRESH_TOKEN] == "mock-refresh-token"
        assert result["data"][CONF_ACCESS_TOKEN] == "mock-access-token"

    @pytest.mark.asyncio
    async def test_code_step_shows_form(self):
        flow = PetSafeSmartFeedConfigFlow()
        flow.hass = MagicMock()
        flow._email = "user@example.com"
        flow._client = MagicMock()

        result = await flow.async_step_code(user_input=None)

        assert result["type"] == "form"
        assert result["step_id"] == "code"
        assert result["description_placeholders"]["email"] == "user@example.com"
