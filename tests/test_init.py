"""Tests for PetSafe Smart Feed __init__ (feed service)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.petsafe_smartfeed.api import (
    PetSafeError,
    PetSafeFeederData,
)
from custom_components.petsafe_smartfeed.const import DOMAIN
from custom_components.petsafe_smartfeed.coordinator import PetSafeCoordinator

from conftest import MOCK_FEEDER_API_RESPONSE


def _make_service_call(device_id="dev-123", amount=1, slow_feed=False):
    call = MagicMock()
    call.data = {"device_id": device_id, "amount": amount, "slow_feed": slow_feed}
    return call


def _make_hass_with_coordinator(thing_name="smart_feed_abc123"):
    """Set up a mock hass with device registry and coordinator."""
    feeder = PetSafeFeederData.from_api(MOCK_FEEDER_API_RESPONSE)

    coordinator = MagicMock(spec=PetSafeCoordinator)
    coordinator.client = MagicMock()
    coordinator.client.feed = AsyncMock()
    coordinator.data = {thing_name: feeder}

    # Mock device registry
    device_entry = MagicMock()
    device_entry.identifiers = {(DOMAIN, thing_name)}

    device_registry = MagicMock()
    device_registry.async_get = MagicMock(return_value=device_entry)

    # Mock config entry
    entry = MagicMock()
    entry.entry_id = "test_entry"
    entry.runtime_data = coordinator

    hass = MagicMock()
    hass.services.has_service = MagicMock(return_value=False)
    hass.config_entries.async_entry_ids = MagicMock(return_value=["test_entry"])
    hass.config_entries.async_get_entry = MagicMock(return_value=entry)

    return hass, coordinator, device_registry


class TestFeedService:
    """Test the feed service handler."""

    @pytest.mark.asyncio
    async def test_successful_feed(self):
        hass, coordinator, device_registry = _make_hass_with_coordinator()

        with patch(
            "custom_components.petsafe_smartfeed.__init__.dr.async_get",
            return_value=device_registry,
        ):
            from custom_components.petsafe_smartfeed.__init__ import _register_services

            # Extract the handler by registering then grabbing the call args
            _register_services(hass)
            handler = hass.services.async_register.call_args[0][2]

            call = _make_service_call(device_id="dev-123", amount=2, slow_feed=True)
            await handler(call)

        coordinator.client.feed.assert_called_once_with(
            "smart_feed_abc123", amount=2, slow_feed=True
        )

    @pytest.mark.asyncio
    async def test_device_not_found(self):
        hass, coordinator, device_registry = _make_hass_with_coordinator()
        device_registry.async_get = MagicMock(return_value=None)

        with patch(
            "custom_components.petsafe_smartfeed.__init__.dr.async_get",
            return_value=device_registry,
        ):
            from custom_components.petsafe_smartfeed.__init__ import _register_services

            _register_services(hass)
            handler = hass.services.async_register.call_args[0][2]

            call = _make_service_call(device_id="nonexistent")
            with pytest.raises(ServiceValidationError, match="not found"):
                await handler(call)

    @pytest.mark.asyncio
    async def test_api_error_raises_ha_error(self):
        hass, coordinator, device_registry = _make_hass_with_coordinator()
        coordinator.client.feed = AsyncMock(
            side_effect=PetSafeError("API error")
        )

        with patch(
            "custom_components.petsafe_smartfeed.__init__.dr.async_get",
            return_value=device_registry,
        ):
            from custom_components.petsafe_smartfeed.__init__ import _register_services

            _register_services(hass)
            handler = hass.services.async_register.call_args[0][2]

            call = _make_service_call()
            with pytest.raises(HomeAssistantError, match="Failed to feed"):
                await handler(call)
