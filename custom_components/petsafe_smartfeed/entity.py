"""Base entity for PetSafe Smart Feed."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import PetSafeFeederData
from .const import DOMAIN
from .coordinator import PetSafeCoordinator


class PetSafeEntity(CoordinatorEntity[PetSafeCoordinator]):
    """Base class for PetSafe entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PetSafeCoordinator, thing_name: str) -> None:
        super().__init__(coordinator)
        self._thing_name = thing_name
        feeder = self.feeder_data
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, thing_name)},
            name=feeder.friendly_name,
            manufacturer="PetSafe",
            model="Smart Feed v2",
        )

    @property
    def feeder_data(self) -> PetSafeFeederData:
        """Return the current feeder data from the coordinator."""
        return self.coordinator.data[self._thing_name]
