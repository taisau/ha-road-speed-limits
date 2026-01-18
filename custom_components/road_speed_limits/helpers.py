"""Helper functions for Road Speed Limits integration."""
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import State

_LOGGER = logging.getLogger(__name__)


def get_config_value(entry: ConfigEntry, key: str, default: Any = None) -> Any:
    """Get a config value from either options or data.

    Options take precedence over data to support runtime reconfiguration.

    Args:
        entry: The config entry
        key: The configuration key
        default: Default value if key not found

    Returns:
        The configuration value
    """
    # Check options first (from options flow)
    if entry.options and key in entry.options:
        return entry.options[key]

    # Fall back to data (from initial setup)
    return entry.data.get(key, default)


def get_coordinate_from_entity(
    entity_state: State | None, coordinate_type: str
) -> float | None:
    """Extract latitude or longitude from an entity.

    Supports multiple entity formats:
    1. Entity with latitude/longitude attributes (device_tracker, person, GPS sensors)
    2. Entity with numeric state (separate lat/lon sensors)

    Args:
        entity_state: The entity state object
        coordinate_type: Either "latitude" or "longitude"

    Returns:
        The coordinate value as a float, or None if not found/invalid
    """
    if entity_state is None:
        _LOGGER.warning("Entity state is None")
        return None

    # Try to get from attributes first (most common for GPS entities)
    if hasattr(entity_state, "attributes") and entity_state.attributes:
        coord_value = entity_state.attributes.get(coordinate_type)
        if coord_value is not None:
            try:
                return float(coord_value)
            except (ValueError, TypeError) as err:
                _LOGGER.warning(
                    "Could not convert %s attribute '%s' to float: %s",
                    coordinate_type,
                    coord_value,
                    err,
                )

    # Fall back to entity state (for separate sensor entities)
    try:
        if entity_state.state in ("unavailable", "unknown"):
            _LOGGER.debug(
                "Entity %s is %s, cannot get coordinate", 
                entity_state.entity_id, 
                entity_state.state
            )
            return None
            
        return float(entity_state.state)
    except (ValueError, TypeError) as err:
        _LOGGER.warning(
            "Could not convert entity state '%s' to float for %s: %s",
            entity_state.state,
            coordinate_type,
            err,
        )
        return None


def validate_coordinates(latitude: float | None, longitude: float | None) -> bool:
    """Validate that coordinates are within valid ranges.

    Args:
        latitude: Latitude value (-90 to 90)
        longitude: Longitude value (-180 to 180)

    Returns:
        True if coordinates are valid, False otherwise
    """
    if latitude is None or longitude is None:
        return False

    # Check latitude range
    if not -90 <= latitude <= 90:
        _LOGGER.error("Latitude %s is out of valid range (-90 to 90)", latitude)
        return False

    # Check longitude range
    if not -180 <= longitude <= 180:
        _LOGGER.error("Longitude %s is out of valid range (-180 to 180)", longitude)
        return False

    return True


def convert_speed(speed: int | None, from_unit: str, to_unit: str) -> int | None:
    """Convert speed between units and round to nearest 5 for mph.

    Args:
        speed: Speed value to convert
        from_unit: Source unit (km/h or mph)
        to_unit: Target unit (km/h or mph)

    Returns:
        Converted speed value, or None if input is None
    """
    if speed is None:
        return None

    if from_unit == to_unit:
        # If already in mph, still apply the rounding to multiple of 5
        if to_unit == "mph":
             return (speed // 5) * 5
        return speed

    if from_unit == "km/h" and to_unit == "mph":
        # km/h to mph: divide by 1.609344
        converted = speed / 1.609344
        # Round down to next 5 (e.g. 6.2 -> 5, 27 -> 25)
        return int((converted // 5) * 5)
    elif from_unit == "mph" and to_unit == "km/h":
        # mph to km/h: multiply by 1.609344
        return round(speed * 1.609344)

    return speed
