"""PetSafe Smart Feed integration for Home Assistant."""

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PetSafeClient, PetSafeError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_EMAIL,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN_EXPIRES_AT,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import PetSafeCoordinator

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

FEED_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): str,
        vol.Optional("amount", default=1): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=8)
        ),
        vol.Optional("slow_feed", default=False): bool,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up PetSafe Smart Feed from a config entry."""
    session = async_get_clientsession(hass)
    client = PetSafeClient(
        session=session,
        email=entry.data[CONF_EMAIL],
        id_token=entry.data.get(CONF_ID_TOKEN),
        refresh_token=entry.data.get(CONF_REFRESH_TOKEN),
        access_token=entry.data.get(CONF_ACCESS_TOKEN),
    )
    client.token_expires_at = entry.data.get(CONF_TOKEN_EXPIRES_AT, 0)

    coordinator = PetSafeCoordinator(hass, client, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _register_services(hass: HomeAssistant) -> None:
    """Register the feed service (idempotent)."""
    if hass.services.has_service(DOMAIN, "feed"):
        return

    async def handle_feed(call: ServiceCall) -> None:
        """Handle the feed service call."""
        device_id = call.data["device_id"]
        amount = call.data["amount"]
        slow_feed = call.data["slow_feed"]

        # Resolve device_id to thing_name via device registry
        device_registry = dr.async_get(hass)
        device_entry = device_registry.async_get(device_id)
        if device_entry is None:
            raise ServiceValidationError(f"Device {device_id} not found")

        thing_name = None
        for identifier in device_entry.identifiers:
            if identifier[0] == DOMAIN:
                thing_name = identifier[1]
                break

        if thing_name is None:
            raise ServiceValidationError(
                f"Device {device_id} is not a PetSafe Smart Feed device"
            )

        # Find the coordinator for this device
        coordinator: PetSafeCoordinator | None = None
        for entry_id in hass.config_entries.async_entry_ids(DOMAIN):
            entry = hass.config_entries.async_get_entry(entry_id)
            if entry and hasattr(entry, "runtime_data"):
                coord = entry.runtime_data
                if isinstance(coord, PetSafeCoordinator) and thing_name in coord.data:
                    coordinator = coord
                    break

        if coordinator is None:
            raise ServiceValidationError(
                f"No active PetSafe coordinator found for device {device_id}"
            )

        try:
            await coordinator.client.feed(thing_name, amount=amount, slow_feed=slow_feed)
        except PetSafeError as err:
            raise HomeAssistantError(f"Failed to feed: {err}") from err

        _LOGGER.info(
            "Fed %d/8 cup(s) via %s (slow_feed=%s)", amount, thing_name, slow_feed
        )

    hass.services.async_register(DOMAIN, "feed", handle_feed, schema=FEED_SERVICE_SCHEMA)
