"""DataUpdateCoordinator for PetSafe Smart Feed."""

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PetSafeAuthError, PetSafeClient, PetSafeError, PetSafeFeederData
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    MIN_API_INTERVAL,
)

_POLL_INTERVAL = timedelta(seconds=MIN_API_INTERVAL)

_LOGGER = logging.getLogger(__name__)


class PetSafeCoordinator(DataUpdateCoordinator[dict[str, PetSafeFeederData]]):
    """Coordinator that fetches feeder data from PetSafe API."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: PetSafeClient,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=_POLL_INTERVAL,
            config_entry=entry,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, PetSafeFeederData]:
        """Fetch feeder data from the PetSafe API."""
        try:
            feeders = await self.client.get_feeders()
        except PetSafeAuthError as err:
            self._persist_tokens()
            raise ConfigEntryAuthFailed(
                "PetSafe authentication failed, please re-authenticate"
            ) from err
        except (PetSafeError, Exception) as err:
            raise UpdateFailed(f"Error communicating with PetSafe: {err}") from err

        self._persist_tokens()

        return {feeder.thing_name: feeder for feeder in feeders}

    def _persist_tokens(self) -> None:
        """Save rotated tokens back to the config entry if changed."""
        entry_data = self.config_entry.data
        if (
            self.client.id_token != entry_data.get(CONF_ID_TOKEN)
            or self.client.refresh_token != entry_data.get(CONF_REFRESH_TOKEN)
            or self.client.access_token != entry_data.get(CONF_ACCESS_TOKEN)
        ):
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **entry_data,
                    CONF_ID_TOKEN: self.client.id_token,
                    CONF_REFRESH_TOKEN: self.client.refresh_token,
                    CONF_ACCESS_TOKEN: self.client.access_token,
                },
            )
            _LOGGER.debug("Persisted refreshed tokens to config entry")
