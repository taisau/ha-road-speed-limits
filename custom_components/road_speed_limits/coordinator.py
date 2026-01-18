"""DataUpdateCoordinator for Road Speed Limits."""
import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DATA_SOURCE_HERE,
    DATA_SOURCE_OSM,
    DATA_SOURCE_TOMTOM,
    DEFAULT_UNIT,
    DOMAIN,
    UPDATE_INTERVAL,
)
from .helpers import convert_speed
from .providers import (
    BaseSpeedLimitProvider,
    HERESpeedLimitProvider,
    OSMSpeedLimitProvider,
    TomTomSpeedLimitProvider,
)

_LOGGER = logging.getLogger(__name__)


class RoadSpeedLimitsCoordinator(DataUpdateCoordinator):
    """Class to manage fetching speed limit data from multiple sources."""

    def __init__(
        self,
        hass: HomeAssistant,
        latitude: float,
        longitude: float,
        data_source: str = DATA_SOURCE_OSM,
        unit_preference: str = DEFAULT_UNIT,
        tomtom_api_key: str | None = None,
        here_api_key: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.latitude = latitude
        self.longitude = longitude
        self.data_source = data_source
        self.unit_preference = unit_preference
        self.fallback_active = False
        self.active_provider_name = None

        # Initialize providers dict
        self.providers: dict[str, BaseSpeedLimitProvider] = {}
        
        # Always add OSM
        self.providers[DATA_SOURCE_OSM] = OSMSpeedLimitProvider()
        
        # Add TomTom if key is present
        if tomtom_api_key:
            self.providers[DATA_SOURCE_TOMTOM] = TomTomSpeedLimitProvider(tomtom_api_key)
            
        # Add HERE if key is present
        if here_api_key:
            self.providers[DATA_SOURCE_HERE] = HERESpeedLimitProvider(here_api_key)

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch speed limit data from all configured providers."""
        results = {}
        
        # Create tasks for all providers
        tasks = {
            name: self.hass.async_create_task(
                provider.fetch_speed_limit(self.latitude, self.longitude)
            )
            for name, provider in self.providers.items()
        }
        
        # Wait for all to complete, handling exceptions individually
        for name, task in tasks.items():
            try:
                data = await task
                results[name] = self._apply_unit_conversion(data)
            except Exception as err:
                _LOGGER.warning("Provider %s failed: %s", name, err)
                results[name] = None

        # Determine if the primary source succeeded
        primary_data = results.get(self.data_source)
        
        if primary_data is not None:
            # Primary succeeded
            if self.fallback_active and self.data_source != DATA_SOURCE_OSM:
                _LOGGER.info("Primary provider %s recovered", self.data_source)
                self.fallback_active = False
            self.active_provider_name = self.providers[self.data_source].get_provider_name()
        
        elif self.data_source != DATA_SOURCE_OSM:
            # Primary failed, check fallback (OSM)
            _LOGGER.warning("Primary provider %s failed, checking fallback", self.data_source)
            self.fallback_active = True
            
            if results.get(DATA_SOURCE_OSM) is not None:
                self.active_provider_name = self.providers[DATA_SOURCE_OSM].get_provider_name()
            else:
                # Both failed
                _LOGGER.error("Both primary and fallback providers failed")
                # We don't raise UpdateFailed here because we want partial results for other sensors
                # but the main sensor will show 'unknown' or old data

        return results

    def get_primary_data(self) -> dict[str, Any] | None:
        """Get data for the configured primary provider with multi-stage fallback."""
        # 1. Try selected primary source
        primary_res = self.data.get(self.data_source)
        if primary_res and primary_res.get("speed_limit") is not None:
            return primary_res

        # Define fallback order: HERE -> TomTom -> OSM
        fallback_order = [DATA_SOURCE_HERE, DATA_SOURCE_TOMTOM, DATA_SOURCE_OSM]
        
        for source in fallback_order:
            if source == self.data_source:
                continue # Already tried as primary
                
            res = self.data.get(source)
            if res and res.get("speed_limit") is not None:
                # Found a working fallback with actual data
                if not self.fallback_active:
                     _LOGGER.info("Primary %s has no data, falling back to %s", self.data_source, source)
                     self.fallback_active = True
                
                # Update active provider name for attributes
                self.active_provider_name = self.providers[source].get_provider_name()
                return res

        return primary_res # Return the primary (empty) result if all fallbacks fail

    def _apply_unit_conversion(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply unit conversion to fetched data based on user preference.

        Args:
            data: Raw data from provider

        Returns:
            Data with converted speed limit and corrected unit
        """
        if not data or data.get("speed_limit") is None:
            return data

        # Create a copy to avoid mutating original if needed elsewhere (though here it's fresh)
        data = data.copy()
        
        source_unit = data.get("unit")
        if source_unit and source_unit != self.unit_preference:
            # Convert speed limit to user's preferred unit
            converted_speed = convert_speed(
                data["speed_limit"], source_unit, self.unit_preference
            )
            data["speed_limit"] = converted_speed
            data["unit"] = self.unit_preference

        return data

    def update_location(self, latitude: float, longitude: float) -> None:
        """Update the coordinates to search."""
        self.latitude = latitude
        self.longitude = longitude
