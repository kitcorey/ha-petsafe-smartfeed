"""Binary sensor platform for PetSafe Smart Feed."""

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import PetSafeCoordinator
from .entity import PetSafeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PetSafe binary sensors."""
    coordinator: PetSafeCoordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = []
    for thing_name in coordinator.data:
        entities.append(PetSafeSettingsSyncedSensor(coordinator, thing_name))
    async_add_entities(entities)


class PetSafeSettingsSyncedSensor(PetSafeEntity, BinarySensorEntity):
    """Binary sensor that indicates whether feeder settings are synced."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "settings_synced"

    def __init__(self, coordinator: PetSafeCoordinator, thing_name: str) -> None:
        super().__init__(coordinator, thing_name)
        self._attr_unique_id = f"{thing_name}_settings_synced"

    @property
    def is_on(self) -> bool:
        """Return True when settings are NOT synced (problem)."""
        return not self.feeder_data.revision_synced

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "revision_desired": self.feeder_data.revision_desired,
            "revision_reported": self.feeder_data.revision_reported,
        }
