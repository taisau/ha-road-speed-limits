"""Data providers for Road Speed Limits integration."""
from abc import ABC, abstractmethod
import logging
from typing import Any

import aiohttp
import async_timeout

from .const import (
    DATA_SOURCE_NAMES,
    DATA_SOURCE_OSM,
    DATA_SOURCE_TOMTOM,
    DATA_SOURCE_HERE,
    HERE_API_URL,
    OSM_OVERPASS_URL,
    OSM_SEARCH_RADIUS,
    TOMTOM_API_URL,
)

_LOGGER = logging.getLogger(__name__)


class BaseSpeedLimitProvider(ABC):
    """Abstract base class for speed limit data providers."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the provider."""
        self.api_key = api_key

    @abstractmethod
    async def fetch_speed_limit(
        self, latitude: float, longitude: float
    ) -> dict[str, Any]:
        """Fetch speed limit data for given coordinates.

        Returns dict with keys:
        - speed_limit: int | None
        - road_name: str | None
        - unit: str (km/h or mph)
        """

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the display name of this provider."""


class OSMSpeedLimitProvider(BaseSpeedLimitProvider):
    """OpenStreetMap speed limit provider."""

    def get_provider_name(self) -> str:
        """Return the display name of this provider."""
        return DATA_SOURCE_NAMES[DATA_SOURCE_OSM]

    async def fetch_speed_limit(
        self, latitude: float, longitude: float
    ) -> dict[str, Any]:
        """Query OpenStreetMap Overpass API for speed limit data."""
        # Construct Overpass query
        query = f"""
        [out:json];
        (
          way(around:{OSM_SEARCH_RADIUS},{latitude},{longitude})["maxspeed"];
          node(around:{OSM_SEARCH_RADIUS},{latitude},{longitude})["maxspeed"];
        );
        out body;
        """

        async with aiohttp.ClientSession() as session:
            async with async_timeout.timeout(10):
                async with session.post(
                    OSM_OVERPASS_URL,
                    data={"data": query},
                ) as response:
                    if response.status != 200:
                        raise Exception(f"OSM API returned status {response.status}")

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


class TomTomSpeedLimitProvider(BaseSpeedLimitProvider):
    """TomTom speed limit provider."""

    def get_provider_name(self) -> str:
        """Return the display name of this provider."""
        return DATA_SOURCE_NAMES[DATA_SOURCE_TOMTOM]

    async def fetch_speed_limit(
        self, latitude: float, longitude: float
    ) -> dict[str, Any]:
        """Query TomTom Traffic API for speed limit data."""
        if not self.api_key:
            raise Exception("TomTom API key not configured")

        params = {
            "point": f"{latitude},{longitude}",
            "key": self.api_key,
            "unit": "KMPH",
        }

        async with aiohttp.ClientSession() as session:
            async with async_timeout.timeout(10):
                async with session.get(TOMTOM_API_URL, params=params) as response:
                    if response.status == 403:
                        raise Exception("TomTom API key is invalid or expired")
                    if response.status != 200:
                        raise Exception(
                            f"TomTom API returned status {response.status}"
                        )

                    data = await response.json()
                    return self._parse_tomtom_response(data)

    def _parse_tomtom_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse TomTom response and extract speed limit."""
        try:
            flow_data = data.get("flowSegmentData", {})

            # Get speed limit from response
            speed_limit = flow_data.get("speedLimit")

            # Get road name if available
            road_name = flow_data.get("frc")  # Functional Road Class
            if road_name:
                # Convert FRC to more readable format
                road_name = f"Road Class {road_name}"

            return {
                "speed_limit": speed_limit if speed_limit else None,
                "road_name": road_name,
                "unit": "km/h",
            }
        except (KeyError, TypeError) as err:
            _LOGGER.warning("Could not parse TomTom response: %s", err)
            return {
                "speed_limit": None,
                "road_name": None,
                "unit": "km/h",
            }


class HERESpeedLimitProvider(BaseSpeedLimitProvider):
    """HERE Maps speed limit provider."""

    def get_provider_name(self) -> str:
        """Return the display name of this provider."""
        return DATA_SOURCE_NAMES[DATA_SOURCE_HERE]

    async def fetch_speed_limit(
        self, latitude: float, longitude: float
    ) -> dict[str, Any]:
        """Query HERE Flow API for speed limit data."""
        if not self.api_key:
            raise Exception("HERE API key not configured")

        params = {
            "locationReferencing": "shape",
            "in": f"circle:{latitude},{longitude};r=50",
            "apiKey": self.api_key,
        }

        async with aiohttp.ClientSession() as session:
            async with async_timeout.timeout(10):
                async with session.get(HERE_API_URL, params=params) as response:
                    if response.status == 401 or response.status == 403:
                        raise Exception("HERE API key is invalid or expired")
                    if response.status != 200:
                        raise Exception(f"HERE API returned status {response.status}")

                    data = await response.json()
                    return self._parse_here_response(data)

    def _parse_here_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse HERE response and extract speed limit."""
        try:
            results = data.get("results", [])

            if not results:
                _LOGGER.debug("No speed limit data found in HERE response")
                return {
                    "speed_limit": None,
                    "road_name": None,
                    "unit": "km/h",
                }

            # Get first result
            first_result = results[0]
            current_flow = first_result.get("currentFlow", {})

            # Get speed limit (in km/h)
            speed_limit = current_flow.get("speedLimit")

            # Get road name if available
            location = first_result.get("location", {})
            road_name = location.get("description")

            return {
                "speed_limit": speed_limit if speed_limit else None,
                "road_name": road_name,
                "unit": "km/h",
            }
        except (KeyError, TypeError, IndexError) as err:
            _LOGGER.warning("Could not parse HERE response: %s", err)
            return {
                "speed_limit": None,
                "road_name": None,
                "unit": "km/h",
            }
