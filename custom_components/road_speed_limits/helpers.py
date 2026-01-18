"""Helper functions for Road Speed Limits integration."""
import logging
from typing import Any

from homeassistant.core import State

_LOGGER = logging.getLogger(__name__)


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
