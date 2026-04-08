"""Tests for PetSafe Smart Feed binary sensors."""

from unittest.mock import MagicMock

import pytest

from custom_components.petsafe_smartfeed.api import PetSafeFeederData
from custom_components.petsafe_smartfeed.binary_sensor import (
    PetSafeSettingsSyncedSensor,
)

from conftest import MOCK_FEEDER_API_RESPONSE


def _make_coordinator(feeder_response: dict):
    feeder = PetSafeFeederData.from_api(feeder_response)
    coordinator = MagicMock()
    coordinator.data = {feeder.thing_name: feeder}
    return coordinator, feeder.thing_name


class TestSettingsSyncedSensor:
    """Test settings synced binary sensor."""

    def test_synced(self):
        # Default mock has revision_desired == revision_reported == 5
        coordinator, thing_name = _make_coordinator(MOCK_FEEDER_API_RESPONSE)
        sensor = PetSafeSettingsSyncedSensor(coordinator, thing_name)

        assert sensor.is_on is False  # No problem

    def test_not_synced(self):
        response = {
            **MOCK_FEEDER_API_RESPONSE,
            "revision_desired": 10,
            "revision_reported": 9,
        }
        coordinator, thing_name = _make_coordinator(response)
        sensor = PetSafeSettingsSyncedSensor(coordinator, thing_name)

        assert sensor.is_on is True  # Problem detected

    def test_extra_attributes(self):
        response = {
            **MOCK_FEEDER_API_RESPONSE,
            "revision_desired": 12,
            "revision_reported": 9,
        }
        coordinator, thing_name = _make_coordinator(response)
        sensor = PetSafeSettingsSyncedSensor(coordinator, thing_name)

        attrs = sensor.extra_state_attributes
        assert attrs["revision_desired"] == 12
        assert attrs["revision_reported"] == 9

    def test_unique_id(self):
        coordinator, thing_name = _make_coordinator(MOCK_FEEDER_API_RESPONSE)
        sensor = PetSafeSettingsSyncedSensor(coordinator, thing_name)

        assert sensor.unique_id == f"{thing_name}_settings_synced"
