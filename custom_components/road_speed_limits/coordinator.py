"""DataUpdateCoordinator for Road Speed Limits."""
from datetime import timedelta
import logging
from typing import Any

import aiohttp
import async_timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    OSM_OVERPASS_URL,
    OSM_SEARCH_RADIUS,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class RoadSpeedLimitsCoordinator(DataUpdateCoordinator):
    """Class to manage fetching speed limit data from OpenStreetMap."""

    def __init__(self, hass: HomeAssistant, latitude: float, longitude: float) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.latitude = latitude
        self.longitude = longitude

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch speed limit data from OpenStreetMap."""
        try:
            async with async_timeout.timeout(10):
                return await self._fetch_speed_limit()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with OSM API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    async def _fetch_speed_limit(self) -> dict[str, Any]:
        """Query OpenStreetMap Overpass API for speed limit data."""
        # Construct Overpass query
        query = f"""
        [out:json];
        (
          way(around:{OSM_SEARCH_RADIUS},{self.latitude},{self.longitude})["maxspeed"];
          node(around:{OSM_SEARCH_RADIUS},{self.latitude},{self.longitude})["maxspeed"];
        );
        out body;
        """

        async with aiohttp.ClientSession() as session:
            async with session.post(
                OSM_OVERPASS_URL,
                data={"data": query},
            ) as response:
                if response.status != 200:
                    raise UpdateFailed(
                        f"OSM API returned status {response.status}"
                    )

                data = await response.json()
                return self._parse_osm_response(data)

    def _parse_osm_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse OpenStreetMap response and extract speed limit."""
        elements = data.get("elements", [])

        if not elements:
            _LOGGER.debug("No speed limit data found at coordinates")
            return {
                "speed_limit": None,
                "road_name": None,
                "unit": None,
            }

        # Take the first element with maxspeed
        for element in elements:
            tags = element.get("tags", {})
            maxspeed = tags.get("maxspeed")

            if maxspeed:
                # Parse speed limit (can be "50", "50 mph", "50 km/h", etc.)
                speed_value, unit = self._parse_speed_value(maxspeed)
                road_name = tags.get("name")

                return {
                    "speed_limit": speed_value,
                    "road_name": road_name,
                    "unit": unit,
                }

        return {
            "speed_limit": None,
            "road_name": None,
            "unit": None,
        }

    def _parse_speed_value(self, maxspeed: str) -> tuple[int | None, str]:
        """Parse maxspeed value and extract numeric value and unit."""
        maxspeed = maxspeed.strip().lower()

        # Handle special values
        if maxspeed in ["none", "unlimited"]:
            return None, "km/h"

        # Try to extract numeric value
        try:
            # Check if unit is specified
            if "mph" in maxspeed:
                speed = int(maxspeed.replace("mph", "").strip())
                return speed, "mph"
            elif "km/h" in maxspeed or "kmh" in maxspeed:
                speed = int(
                    maxspeed.replace("km/h", "").replace("kmh", "").strip()
                )
                return speed, "km/h"
            else:
                # No unit specified, assume km/h (OSM default)
                speed = int(maxspeed)
                return speed, "km/h"
        except ValueError:
            _LOGGER.warning("Could not parse speed limit value: %s", maxspeed)
            return None, "km/h"

    def update_location(self, latitude: float, longitude: float) -> None:
        """Update the coordinates to search."""
        self.latitude = latitude
        self.longitude = longitude
