"""Sensor platform for Road Speed Limits integration."""
from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ACTIVE_PROVIDER,
    ATTR_DATA_SOURCE,
    ATTR_FALLBACK_ACTIVE,
    ATTR_LAST_UPDATE,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    ATTR_ROAD_NAME,
    DATA_SOURCE_NAMES,
    DEFAULT_NAME,
    DOMAIN,
)
from .coordinator import RoadSpeedLimitsCoordinator
from .helpers import get_coordinate_from_entity, validate_coordinates

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Road Speed Limits sensor."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    lat_entity_id = hass.data[DOMAIN][entry.entry_id]["lat_entity_id"]
    lon_entity_id = hass.data[DOMAIN][entry.entry_id]["lon_entity_id"]

    async_add_entities(
        [RoadSpeedLimitSensor(coordinator, entry, lat_entity_id, lon_entity_id)]
    )


class RoadSpeedLimitSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Road Speed Limit sensor."""

    def __init__(
        self,
        coordinator: RoadSpeedLimitsCoordinator,
        entry: ConfigEntry,
        lat_entity_id: str,
        lon_entity_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = DEFAULT_NAME
        self._attr_unique_id = f"{entry.entry_id}_speed_limit"
        self._lat_entity_id = lat_entity_id
        self._lon_entity_id = lon_entity_id
        self._attr_icon = "mdi:speedometer"

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("speed_limit")
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        if self.coordinator.data:
            return self.coordinator.data.get("unit")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        # Get selected data source display name
        selected_source = DATA_SOURCE_NAMES.get(
            self.coordinator.data_source, self.coordinator.data_source
        )

        attributes = {
            ATTR_DATA_SOURCE: selected_source,
            ATTR_ACTIVE_PROVIDER: self.coordinator.active_provider_name,
            ATTR_FALLBACK_ACTIVE: self.coordinator.fallback_active,
            ATTR_LAST_UPDATE: datetime.now().isoformat(),
            ATTR_LATITUDE: self.coordinator.latitude,
            ATTR_LONGITUDE: self.coordinator.longitude,
        }

        if self.coordinator.data:
            road_name = self.coordinator.data.get("road_name")
            if road_name:
                attributes[ATTR_ROAD_NAME] = road_name

        return attributes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Update location if entities changed
        lat_state = self.hass.states.get(self._lat_entity_id)
        lon_state = self.hass.states.get(self._lon_entity_id)

        if lat_state and lon_state:
            # Extract coordinates (supports both attributes and state)
            new_lat = get_coordinate_from_entity(lat_state, "latitude")
            new_lon = get_coordinate_from_entity(lon_state, "longitude")

            # Validate and update if coordinates are valid and changed
            if validate_coordinates(new_lat, new_lon):
                if (
                    new_lat != self.coordinator.latitude
                    or new_lon != self.coordinator.longitude
                ):
                    self.coordinator.update_location(new_lat, new_lon)
                    _LOGGER.debug("Updated location to %s, %s", new_lat, new_lon)
            else:
                _LOGGER.warning(
                    "Invalid coordinate values from entities: lat=%s, lon=%s",
                    new_lat,
                    new_lon,
                )

        super()._handle_coordinator_update()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success and self.coordinator.data is not None
