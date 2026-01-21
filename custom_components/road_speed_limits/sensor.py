"""Sensor platform for Road Speed Limits integration."""
from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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
    DATA_SOURCE_OSM,
    DATA_SOURCE_TOMTOM,
    DATA_SOURCE_HERE,
    DEFAULT_NAME,
    DOMAIN,
)
from .coordinator import RoadSpeedLimitsCoordinator

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
    speed_entity_id = hass.data[DOMAIN][entry.entry_id].get("speed_entity_id")

    entities = []

    # 1. Create the Primary Sensor (Original behavior)
    entities.append(
        RoadSpeedLimitSensor(coordinator, entry, lat_entity_id, lon_entity_id, speed_entity_id)
    )

    # 2. Create specific sensors for each available provider
    # Always create OSM
    entities.append(
        SourceSpecificSpeedLimitSensor(
            coordinator, entry, DATA_SOURCE_OSM, "OSM"
        )
    )

    # Create TomTom if configured
    if DATA_SOURCE_TOMTOM in coordinator.providers:
        entities.append(
            SourceSpecificSpeedLimitSensor(
                coordinator, entry, DATA_SOURCE_TOMTOM, "TomTom"
            )
        )

    # Create HERE if configured
    if DATA_SOURCE_HERE in coordinator.providers:
        entities.append(
            SourceSpecificSpeedLimitSensor(
                coordinator, entry, DATA_SOURCE_HERE, "HERE"
            )
        )

    async_add_entities(entities)


class RoadSpeedLimitSensor(CoordinatorEntity, SensorEntity):
    """Representation of the primary Road Speed Limit sensor."""

    def __init__(
        self,
        coordinator: RoadSpeedLimitsCoordinator,
        entry: ConfigEntry,
        lat_entity_id: str,
        lon_entity_id: str,
        speed_entity_id: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = DEFAULT_NAME
        self._attr_unique_id = f"{entry.entry_id}_speed_limit"
        self._lat_entity_id = lat_entity_id
        self._lon_entity_id = lon_entity_id
        self._speed_entity_id = speed_entity_id
        self._attr_icon = "mdi:speedometer"

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        data = self.coordinator.get_primary_data()
        if data:
            return data.get("speed_limit")
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        data = self.coordinator.get_primary_data()
        if data:
            return data.get("unit")
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

        data = self.coordinator.get_primary_data()
        if data:
            road_name = data.get("road_name")
            if road_name:
                attributes[ATTR_ROAD_NAME] = road_name

        return attributes

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # Available if coordinator ran successfully at least once
        return self.coordinator.last_update_success

    @property
    def should_poll(self) -> bool:
        """Disable default Home Assistant polling."""
        return False


class SourceSpecificSpeedLimitSensor(CoordinatorEntity, SensorEntity):
    """Representation of a specific source speed limit sensor (e.g., just TomTom)."""

    def __init__(
        self,
        coordinator: RoadSpeedLimitsCoordinator,
        entry: ConfigEntry,
        source_key: str,
        source_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.source_key = source_key
        self._attr_name = f"Road Speed Limit {source_name}"
        self._attr_unique_id = f"{entry.entry_id}_speed_limit_{source_key}"
        self._attr_icon = "mdi:speedometer"

        # Use suggested_object_id instead of entity_id (Issue 8)
        # This allows HA to apply its naming rules while suggesting our preferred ID
        self._attr_suggested_object_id = f"road_speed_limit_{source_key}"

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
        
        source_data = self.coordinator.data.get(self.source_key)
        if source_data:
            return source_data.get("speed_limit")
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        if not self.coordinator.data:
            return None
            
        source_data = self.coordinator.data.get(self.source_key)
        if source_data:
            return source_data.get("unit")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        attributes = {
            ATTR_DATA_SOURCE: DATA_SOURCE_NAMES.get(self.source_key, self.source_key),
            ATTR_LAST_UPDATE: datetime.now().isoformat(),
        }

        if self.coordinator.data:
            source_data = self.coordinator.data.get(self.source_key)
            if source_data:
                road_name = source_data.get("road_name")
                if road_name:
                    attributes[ATTR_ROAD_NAME] = road_name

        return attributes

    @property
    def should_poll(self) -> bool:
        """Disable default Home Assistant polling."""
        return False