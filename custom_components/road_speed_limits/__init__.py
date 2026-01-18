"""The Road Speed Limits integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DATA_SOURCE,
    CONF_LATITUDE_ENTITY,
    CONF_LONGITUDE_ENTITY,
    DEFAULT_DATA_SOURCE,
    DOMAIN,
    HERE_API_KEY_NAME,
    TOMTOM_API_KEY_NAME,
)
from .coordinator import RoadSpeedLimitsCoordinator
from .helpers import get_coordinate_from_entity, validate_coordinates

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Road Speed Limits from a config entry."""
    # Get entity IDs from config
    lat_entity_id = entry.data[CONF_LATITUDE_ENTITY]
    lon_entity_id = entry.data[CONF_LONGITUDE_ENTITY]

    # Get data source (default to OSM for backward compatibility)
    data_source = entry.data.get(CONF_DATA_SOURCE, DEFAULT_DATA_SOURCE)

    # Get initial coordinates from entities
    lat_state = hass.states.get(lat_entity_id)
    lon_state = hass.states.get(lon_entity_id)

    if lat_state is None or lon_state is None:
        _LOGGER.error("Could not get initial coordinates from entities")
        return False

    # Extract coordinates (supports both attributes and state)
    latitude = get_coordinate_from_entity(lat_state, "latitude")
    longitude = get_coordinate_from_entity(lon_state, "longitude")

    # Validate coordinates
    if not validate_coordinates(latitude, longitude):
        _LOGGER.error(
            "Invalid coordinate values from entities: lat=%s, lon=%s",
            latitude,
            longitude,
        )
        return False

    # Load API keys from secrets
    tomtom_api_key = None
    here_api_key = None

    try:
        secrets = await hass.helpers.secrets.async_load_secrets()
        tomtom_api_key = secrets.get(TOMTOM_API_KEY_NAME)
        here_api_key = secrets.get(HERE_API_KEY_NAME)

        if not tomtom_api_key:
            _LOGGER.debug("TomTom API key not found in secrets.yaml")
        if not here_api_key:
            _LOGGER.debug("HERE API key not found in secrets.yaml")

    except Exception as err:
        _LOGGER.warning("Could not load secrets.yaml: %s", err)

    # Create coordinator
    coordinator = RoadSpeedLimitsCoordinator(
        hass,
        latitude,
        longitude,
        data_source=data_source,
        tomtom_api_key=tomtom_api_key,
        here_api_key=here_api_key,
    )

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

    # Set up options update listener
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
