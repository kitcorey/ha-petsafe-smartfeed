"""Tests for PetSafe Smart Feed switches."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.petsafe_smartfeed.api import (
    PetSafeError,
    PetSafeFeederData,
)
from custom_components.petsafe_smartfeed.switch import (
    PetSafeSwitch,
    SWITCH_DESCRIPTIONS,
)

from conftest import MOCK_FEEDER_API_RESPONSE


def _make_coordinator(feeder_response: dict):
    feeder = PetSafeFeederData.from_api(feeder_response)
    coordinator = MagicMock()
    coordinator.data = {feeder.thing_name: feeder}
    coordinator.client = MagicMock()
    coordinator.client.set_setting = AsyncMock()
    return coordinator, feeder.thing_name


class TestPetSafeSwitch:
    """Test PetSafe switch entities."""

    def test_slow_feed_off(self):
        coordinator, thing_name = _make_coordinator(MOCK_FEEDER_API_RESPONSE)
        desc = SWITCH_DESCRIPTIONS[0]  # slow_feed
        switch = PetSafeSwitch(coordinator, thing_name, desc)

        assert switch.is_on is False

    def test_slow_feed_on(self):
        response = {
            **MOCK_FEEDER_API_RESPONSE,
            "settings": {**MOCK_FEEDER_API_RESPONSE["settings"], "slow_feed": True},
        }
        coordinator, thing_name = _make_coordinator(response)
        desc = SWITCH_DESCRIPTIONS[0]  # slow_feed
        switch = PetSafeSwitch(coordinator, thing_name, desc)

        assert switch.is_on is True

    @pytest.mark.asyncio
    async def test_turn_on(self):
        coordinator, thing_name = _make_coordinator(MOCK_FEEDER_API_RESPONSE)
        desc = SWITCH_DESCRIPTIONS[0]  # slow_feed
        switch = PetSafeSwitch(coordinator, thing_name, desc)
        switch.async_write_ha_state = MagicMock()

        await switch.async_turn_on()

        coordinator.client.set_setting.assert_called_once_with(
            thing_name, "slow_feed", True
        )
        # Optimistic update
        assert switch.is_on is True
        switch.async_write_ha_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_off(self):
        response = {
            **MOCK_FEEDER_API_RESPONSE,
            "settings": {**MOCK_FEEDER_API_RESPONSE["settings"], "slow_feed": True},
        }
        coordinator, thing_name = _make_coordinator(response)
        desc = SWITCH_DESCRIPTIONS[0]  # slow_feed
        switch = PetSafeSwitch(coordinator, thing_name, desc)
        switch.async_write_ha_state = MagicMock()

        await switch.async_turn_off()

        coordinator.client.set_setting.assert_called_once_with(
            thing_name, "slow_feed", False
        )
        assert switch.is_on is False

    @pytest.mark.asyncio
    async def test_set_error_raises_ha_error(self):
        coordinator, thing_name = _make_coordinator(MOCK_FEEDER_API_RESPONSE)
        coordinator.client.set_setting = AsyncMock(
            side_effect=PetSafeError("API error")
        )
        desc = SWITCH_DESCRIPTIONS[0]
        switch = PetSafeSwitch(coordinator, thing_name, desc)

        with pytest.raises(HomeAssistantError, match="Failed to set"):
            await switch.async_turn_on()

    def test_all_switches_unique_ids(self):
        coordinator, thing_name = _make_coordinator(MOCK_FEEDER_API_RESPONSE)
        unique_ids = set()
        for desc in SWITCH_DESCRIPTIONS:
            switch = PetSafeSwitch(coordinator, thing_name, desc)
            unique_ids.add(switch.unique_id)

        assert len(unique_ids) == len(SWITCH_DESCRIPTIONS)

    def test_paused_switch(self):
        coordinator, thing_name = _make_coordinator(MOCK_FEEDER_API_RESPONSE)
        desc = SWITCH_DESCRIPTIONS[1]  # paused
        switch = PetSafeSwitch(coordinator, thing_name, desc)

        assert switch.is_on is False
        assert switch.unique_id == f"{thing_name}_paused"

    def test_child_lock_switch(self):
        coordinator, thing_name = _make_coordinator(MOCK_FEEDER_API_RESPONSE)
        desc = SWITCH_DESCRIPTIONS[2]  # child_lock
        switch = PetSafeSwitch(coordinator, thing_name, desc)

        assert switch.is_on is False
        assert switch.unique_id == f"{thing_name}_child_lock"
