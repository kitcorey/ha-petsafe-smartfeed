"""Tests for PetSafe Smart Feed sensors."""

from unittest.mock import MagicMock

import pytest

from custom_components.petsafe_smartfeed.api import PetSafeFeederData
from custom_components.petsafe_smartfeed.sensor import (
    PetSafeBatterySensor,
    PetSafeFoodLevelSensor,
    PetSafeWifiSignalSensor,
)

from conftest import MOCK_FEEDER_API_RESPONSE, MOCK_FEEDER_LOW_BATTERY


def _make_coordinator(feeder_response: dict):
    """Create a mock coordinator with feeder data."""
    feeder = PetSafeFeederData.from_api(feeder_response)
    coordinator = MagicMock()
    coordinator.data = {feeder.thing_name: feeder}
    return coordinator, feeder.thing_name


class TestBatterySensor:
    """Test battery level sensor."""

    def test_normal_battery(self):
        coordinator, thing_name = _make_coordinator(MOCK_FEEDER_API_RESPONSE)
        sensor = PetSafeBatterySensor(coordinator, thing_name)

        # battery_voltage=26000 → ~51%
        assert 40 <= sensor.native_value <= 60

    def test_low_battery(self):
        coordinator, thing_name = _make_coordinator(MOCK_FEEDER_LOW_BATTERY)
        sensor = PetSafeBatterySensor(coordinator, thing_name)

        assert sensor.native_value < 10

    def test_unique_id(self):
        coordinator, thing_name = _make_coordinator(MOCK_FEEDER_API_RESPONSE)
        sensor = PetSafeBatterySensor(coordinator, thing_name)

        assert sensor.unique_id == f"{thing_name}_battery_level"

    def test_device_info(self):
        coordinator, thing_name = _make_coordinator(MOCK_FEEDER_API_RESPONSE)
        sensor = PetSafeBatterySensor(coordinator, thing_name)

        assert sensor.device_info is not None
        assert ("petsafe_smartfeed", thing_name) in sensor.device_info["identifiers"]
        assert sensor.device_info["sw_version"] == "V2.0.9"


class TestFoodLevelSensor:
    """Test food level sensor."""

    def test_full(self):
        coordinator, thing_name = _make_coordinator(MOCK_FEEDER_API_RESPONSE)
        sensor = PetSafeFoodLevelSensor(coordinator, thing_name)

        assert sensor.native_value == "Full"

    def test_low(self):
        coordinator, thing_name = _make_coordinator(MOCK_FEEDER_LOW_BATTERY)
        sensor = PetSafeFoodLevelSensor(coordinator, thing_name)

        assert sensor.native_value == "Low"

    def test_empty(self):
        empty_response = {**MOCK_FEEDER_API_RESPONSE, "is_food_low": 2}
        coordinator, thing_name = _make_coordinator(empty_response)
        sensor = PetSafeFoodLevelSensor(coordinator, thing_name)

        assert sensor.native_value == "Empty"

    def test_unique_id(self):
        coordinator, thing_name = _make_coordinator(MOCK_FEEDER_API_RESPONSE)
        sensor = PetSafeFoodLevelSensor(coordinator, thing_name)

        assert sensor.unique_id == f"{thing_name}_food_level"

    def test_options(self):
        coordinator, thing_name = _make_coordinator(MOCK_FEEDER_API_RESPONSE)
        sensor = PetSafeFoodLevelSensor(coordinator, thing_name)

        assert sensor.options == ["Full", "Low", "Empty"]


class TestWifiSignalSensor:
    """Test Wi-Fi signal strength sensor."""

    def test_rssi_value(self):
        coordinator, thing_name = _make_coordinator(MOCK_FEEDER_API_RESPONSE)
        sensor = PetSafeWifiSignalSensor(coordinator, thing_name)

        assert sensor.native_value == -48

    def test_none_when_missing(self):
        response = {**MOCK_FEEDER_API_RESPONSE}
        del response["network_rssi"]
        coordinator, thing_name = _make_coordinator(response)
        sensor = PetSafeWifiSignalSensor(coordinator, thing_name)

        assert sensor.native_value is None

    def test_unique_id(self):
        coordinator, thing_name = _make_coordinator(MOCK_FEEDER_API_RESPONSE)
        sensor = PetSafeWifiSignalSensor(coordinator, thing_name)

        assert sensor.unique_id == f"{thing_name}_wifi_signal"
