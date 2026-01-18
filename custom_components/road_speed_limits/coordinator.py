"""DataUpdateCoordinator for Road Speed Limits."""
from datetime import timedelta
import logging
from typing import Any

import aiohttp
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DATA_SOURCE_HERE,
    DATA_SOURCE_OSM,
    DATA_SOURCE_TOMTOM,
    DOMAIN,
    UPDATE_INTERVAL,
)
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
        self.fallback_active = False
        self.active_provider_name = None

        # Initialize providers
        self.osm_provider = OSMSpeedLimitProvider()

        # Set primary provider based on data source
        if data_source == DATA_SOURCE_TOMTOM:
            self.primary_provider = TomTomSpeedLimitProvider(tomtom_api_key)
        elif data_source == DATA_SOURCE_HERE:
            self.primary_provider = HERESpeedLimitProvider(here_api_key)
        else:
            self.primary_provider = self.osm_provider

        self.active_provider_name = self.primary_provider.get_provider_name()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch speed limit data from configured provider with fallback."""
        # Try primary provider first
        try:
            data = await self.primary_provider.fetch_speed_limit(
                self.latitude, self.longitude
            )
            # Reset fallback if primary provider succeeds
            if self.fallback_active:
                _LOGGER.info(
                    "Primary provider %s recovered, disabling fallback",
                    self.primary_provider.get_provider_name(),
                )
                self.fallback_active = False
            self.active_provider_name = self.primary_provider.get_provider_name()
            return data

        except Exception as err:
            # If primary provider is not OSM, try falling back to OSM
            if self.primary_provider != self.osm_provider:
                _LOGGER.warning(
                    "Primary provider %s failed: %s, falling back to OSM",
                    self.primary_provider.get_provider_name(),
                    err,
                )
                self.fallback_active = True
                try:
                    data = await self.osm_provider.fetch_speed_limit(
                        self.latitude, self.longitude
                    )
                    self.active_provider_name = self.osm_provider.get_provider_name()
                    return data
                except Exception as osm_err:
                    _LOGGER.error("OSM fallback also failed: %s", osm_err)
                    raise UpdateFailed(
                        f"Both primary provider and OSM fallback failed"
                    ) from osm_err
            else:
                # Primary provider is OSM and it failed
                _LOGGER.error("OSM provider failed: %s", err)
                raise UpdateFailed(f"Error fetching speed limit: {err}") from err

    def update_location(self, latitude: float, longitude: float) -> None:
        """Update the coordinates to search."""
        self.latitude = latitude
        self.longitude = longitude
