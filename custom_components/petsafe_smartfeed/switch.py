"""Switch platform for PetSafe Smart Feed."""

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import PetSafeError, PetSafeFeederData
from .const import DOMAIN
from .coordinator import PetSafeCoordinator
from .entity import PetSafeEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class PetSafeSwitchEntityDescription(SwitchEntityDescription):
    """Describes a PetSafe switch entity."""

    setting_key: str
    feeder_attr: str


SWITCH_DESCRIPTIONS: tuple[PetSafeSwitchEntityDescription, ...] = (
    PetSafeSwitchEntityDescription(
        key="slow_feed",
        translation_key="slow_feed",
        setting_key="slow_feed",
        feeder_attr="slow_feed",
        icon="mdi:speedometer-slow",
    ),
    PetSafeSwitchEntityDescription(
        key="paused",
        translation_key="paused",
        setting_key="paused",
        feeder_attr="paused",
        icon="mdi:pause-circle-outline",
    ),
    PetSafeSwitchEntityDescription(
        key="child_lock",
        translation_key="child_lock",
        setting_key="child_lock",
        feeder_attr="child_lock",
        icon="mdi:lock",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up PetSafe switches."""
    coordinator: PetSafeCoordinator = entry.runtime_data
    entities: list[SwitchEntity] = []
    for thing_name in coordinator.data:
        for desc in SWITCH_DESCRIPTIONS:
            entities.append(PetSafeSwitch(coordinator, thing_name, desc))
    async_add_entities(entities)


class PetSafeSwitch(PetSafeEntity, SwitchEntity):
    """A switch for a PetSafe feeder setting."""

    entity_description: PetSafeSwitchEntityDescription

    def __init__(
        self,
        coordinator: PetSafeCoordinator,
        thing_name: str,
        description: PetSafeSwitchEntityDescription,
    ) -> None:
        super().__init__(coordinator, thing_name)
        self.entity_description = description
        self._attr_unique_id = f"{thing_name}_{description.key}"

    @property
    def is_on(self) -> bool:
        return getattr(self.feeder_data, self.entity_description.feeder_attr)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set_value(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_value(False)

    async def _set_value(self, value: bool) -> None:
        try:
            await self.coordinator.client.set_setting(
                self._thing_name, self.entity_description.setting_key, value
            )
        except PetSafeError as err:
            raise HomeAssistantError(
                f"Failed to set {self.entity_description.key}: {err}"
            ) from err
        # Optimistic update: patch the cached feeder data
        feeder = self.feeder_data
        object.__setattr__(feeder, self.entity_description.feeder_attr, value)
        self.async_write_ha_state()
