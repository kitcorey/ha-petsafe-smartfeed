"""Tests for PetSafe Smart Feed coordinator."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.petsafe_smartfeed.api import (
    PetSafeAuthError,
    PetSafeClient,
    PetSafeError,
    PetSafeFeederData,
)
from custom_components.petsafe_smartfeed.const import CONF_ID_TOKEN, DOMAIN
from custom_components.petsafe_smartfeed.coordinator import PetSafeCoordinator

from conftest import MOCK_CONFIG_ENTRY_DATA, MOCK_FEEDER_API_RESPONSE


@pytest.fixture
def mock_client():
    client = MagicMock(spec=PetSafeClient)
    client.id_token = "mock-id-token"
    client.refresh_token = "mock-refresh-token"
    client.access_token = "mock-access-token"
    client.token_expires_at = 0
    feeder = PetSafeFeederData.from_api(MOCK_FEEDER_API_RESPONSE)
    client.get_feeders = AsyncMock(return_value=[feeder])
    return client


@pytest.fixture
def mock_entry():
    entry = MagicMock()
    entry.data = dict(MOCK_CONFIG_ENTRY_DATA)
    entry.entry_id = "test_entry_id"
    return entry


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.config_entries = MagicMock()
    return hass


class TestPetSafeCoordinator:
    """Test the data update coordinator."""

    @pytest.mark.asyncio
    async def test_fetch_data(self, mock_hass, mock_client, mock_entry):
        coordinator = PetSafeCoordinator(mock_hass, mock_client, mock_entry)

        data = await coordinator._async_update_data()

        assert "smart_feed_abc123" in data
        assert data["smart_feed_abc123"].friendly_name == "Kitchen Feeder"
        mock_client.get_feeders.assert_called_once()

    @pytest.mark.asyncio
    async def test_auth_error_raises_config_entry_auth_failed(
        self, mock_hass, mock_client, mock_entry
    ):
        mock_client.get_feeders = AsyncMock(
            side_effect=PetSafeAuthError("Token expired")
        )
        coordinator = PetSafeCoordinator(mock_hass, mock_client, mock_entry)

        with pytest.raises(ConfigEntryAuthFailed):
            await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_api_error_raises_update_failed(
        self, mock_hass, mock_client, mock_entry
    ):
        mock_client.get_feeders = AsyncMock(
            side_effect=PetSafeError("Server error")
        )
        coordinator = PetSafeCoordinator(mock_hass, mock_client, mock_entry)

        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

    @pytest.mark.asyncio
    async def test_token_persistence(self, mock_hass, mock_client, mock_entry):
        # Simulate token rotation
        mock_client.id_token = "new-id-token"
        coordinator = PetSafeCoordinator(mock_hass, mock_client, mock_entry)

        await coordinator._async_update_data()

        # Should have called async_update_entry to persist new tokens
        mock_hass.config_entries.async_update_entry.assert_called_once()
        call_args = mock_hass.config_entries.async_update_entry.call_args
        assert call_args[1]["data"][CONF_ID_TOKEN] == "new-id-token"

    @pytest.mark.asyncio
    async def test_no_persist_when_tokens_unchanged(
        self, mock_hass, mock_client, mock_entry
    ):
        coordinator = PetSafeCoordinator(mock_hass, mock_client, mock_entry)

        await coordinator._async_update_data()

        mock_hass.config_entries.async_update_entry.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_feeders_raises_update_failed(
        self, mock_hass, mock_client, mock_entry
    ):
        mock_client.get_feeders = AsyncMock(return_value=[])
        coordinator = PetSafeCoordinator(mock_hass, mock_client, mock_entry)

        with pytest.raises(UpdateFailed, match="no feeders"):
            await coordinator._async_update_data()
