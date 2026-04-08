"""Sensor platform for PetSafe Smart Feed."""

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, FOOD_STATUS_OPTIONS
from .coordinator import PetSafeCoordinator
from .entity import PetSafeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PetSafe sensors."""
    coordinator: PetSafeCoordinator = entry.runtime_data
    entities: list[SensorEntity] = []
    for thing_name in coordinator.data:
        entities.append(PetSafeBatterySensor(coordinator, thing_name))
        entities.append(PetSafeFoodLevelSensor(coordinator, thing_name))
        entities.append(PetSafeLastSeenSensor(coordinator, thing_name))
    async_add_entities(entities)


class PetSafeBatterySensor(PetSafeEntity, SensorEntity):
    """Battery level sensor."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_translation_key = "battery_level"

    def __init__(self, coordinator: PetSafeCoordinator, thing_name: str) -> None:
        super().__init__(coordinator, thing_name)
        self._attr_unique_id = f"{thing_name}_battery_level"

    @property
    def native_value(self) -> int:
        return self.feeder_data.battery_level

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"battery_voltage": self.feeder_data.battery_voltage}


class PetSafeFoodLevelSensor(PetSafeEntity, SensorEntity):
    """Food level sensor (enum: Full/Low/Empty)."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = FOOD_STATUS_OPTIONS
    _attr_translation_key = "food_level"

    def __init__(self, coordinator: PetSafeCoordinator, thing_name: str) -> None:
        super().__init__(coordinator, thing_name)
        self._attr_unique_id = f"{thing_name}_food_level"

    @property
    def native_value(self) -> str:
        return self.feeder_data.food_low_label


class PetSafeLastSeenSensor(PetSafeEntity, SensorEntity):
    """Last seen timestamp sensor."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "last_seen"

    def __init__(self, coordinator: PetSafeCoordinator, thing_name: str) -> None:
        super().__init__(coordinator, thing_name)
        self._attr_unique_id = f"{thing_name}_last_seen"

    @property
    def native_value(self) -> datetime | None:
        return self.feeder_data.last_seen
