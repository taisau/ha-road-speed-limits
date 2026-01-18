"""The Road Speed Limits integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_LATITUDE_ENTITY, CONF_LONGITUDE_ENTITY, DOMAIN
from .coordinator import RoadSpeedLimitsCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Road Speed Limits from a config entry."""
    # Get entity IDs from config
    lat_entity_id = entry.data[CONF_LATITUDE_ENTITY]
    lon_entity_id = entry.data[CONF_LONGITUDE_ENTITY]

    # Get initial coordinates from entities
    lat_state = hass.states.get(lat_entity_id)
    lon_state = hass.states.get(lon_entity_id)

    if lat_state is None or lon_state is None:
        _LOGGER.error("Could not get initial coordinates from entities")
        return False

    try:
        latitude = float(lat_state.state)
        longitude = float(lon_state.state)
    except (ValueError, TypeError):
        _LOGGER.error("Invalid coordinate values from entities")
        return False

    # Create coordinator
    coordinator = RoadSpeedLimitsCoordinator(hass, latitude, longitude)

    # Store coordinator for platforms to access
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "lat_entity_id": lat_entity_id,
        "lon_entity_id": lon_entity_id,
    }

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Forward setup to sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
