"""Data providers for Road Speed Limits integration."""
from abc import ABC, abstractmethod
from typing import Any
import asyncio
import logging
import math

from .const import (
    DATA_SOURCE_NAMES,
    DATA_SOURCE_OSM,
    DATA_SOURCE_TOMTOM,
    DATA_SOURCE_HERE,
    HERE_API_URL,
    OSM_OVERPASS_URL,
    OSM_SEARCH_RADIUS,
    SpeedLimitData,
    TOMTOM_API_URL,
)

_LOGGER = logging.getLogger(__name__)


def _calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Haversine distance in meters between two points.

    Args:
        lat1: Latitude of first point
        lon1: Longitude of first point
        lat2: Latitude of second point
        lon2: Longitude of second point

    Returns:
        Distance in meters
    """
    # Earth radius in meters
    R = 6371000

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


class BaseSpeedLimitProvider(ABC):
    """Abstract base class for speed limit data providers."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the provider."""
        self.api_key = api_key

    @abstractmethod
    async def fetch_speed_limit(
        self, latitude: float, longitude: float
    ) -> SpeedLimitData:
        """Fetch speed limit data for given coordinates.

        Returns SpeedLimitData with keys:
        - speed_limit: int | None
        - road_name: str | None
        - unit: str (km/h or mph)
        - distance: float | None (distance in meters to the road)
        """

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the display name of this provider."""


class OSMSpeedLimitProvider(BaseSpeedLimitProvider):
    """OpenStreetMap speed limit provider."""

    def __init__(self, api_key: str | None = None, unit_preference: str | None = None) -> None:
        """Initialize the provider."""
        super().__init__(api_key)
        self.unit_preference = unit_preference or "km/h"

    def get_provider_name(self) -> str:
        """Return the display name of this provider."""
        return DATA_SOURCE_NAMES[DATA_SOURCE_OSM]

    async def fetch_speed_limit(
        self, latitude: float, longitude: float
    ) -> SpeedLimitData:
        """Query OpenStreetMap Overpass API for speed limit data."""
        import aiohttp
        import async_timeout

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
            # Retry loop for resilience
            retries = 3
            last_exception = None
            
            for attempt in range(retries):
                try:
                    async with async_timeout.timeout(15):
                        async with session.post(
                            OSM_OVERPASS_URL,
                            data={"data": query},
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                return self._parse_osm_response(data, latitude, longitude)
                            
                            # Handle transient errors (Rate limit, Gateway Timeout, etc.)
                            if response.status in (429, 502, 503, 504):
                                _LOGGER.warning(
                                    "OSM API returned status %s on attempt %d/%d",
                                    response.status,
                                    attempt + 1,
                                    retries
                                )
                                if attempt < retries - 1:
                                    # Exponential backoff: 2s, 4s, etc.
                                    await asyncio.sleep(2 * (attempt + 1))
                                    continue
                                else:
                                    raise aiohttp.ClientError(f"OSM API returned status {response.status}")
                            
                            # Other errors (non-transient)
                            raise aiohttp.ClientError(f"OSM API returned status {response.status}")
                            
                except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                    last_exception = err
                    _LOGGER.debug(
                        "Error connecting to OSM API on attempt %d/%d: %s",
                        attempt + 1,
                        retries,
                        err
                    )
                    if attempt < retries - 1:
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
            
            # If we get here, all retries failed
            raise aiohttp.ClientError(f"OSM API failed after {retries} attempts") from last_exception

    def _parse_osm_response(self, data: dict[str, Any], query_lat: float, query_lon: float) -> SpeedLimitData:
        """Parse OpenStreetMap response and extract speed limit from closest road.

        Args:
            data: OSM response data
            query_lat: Query latitude for distance calculation
            query_lon: Query longitude for distance calculation

        Returns:
            SpeedLimitData with closest road information
        """
        elements = data.get("elements", [])

        if not elements:
            _LOGGER.debug("No speed limit data found at coordinates")
            return {
                "speed_limit": None,
                "road_name": None,
                "unit": None,
                "distance": None,
            }

        # Build list of roads with speed limits and calculate distances
        roads_with_distance = []

        for element in elements:
            tags = element.get("tags", {})
            maxspeed = tags.get("maxspeed")

            if maxspeed:
                # Parse speed limit (can be "50", "50 mph", "50 km/h", etc.)
                speed_value, unit = self._parse_speed_value(maxspeed)
                road_name = tags.get("name")

                # Calculate distance to this road element
                # For ways, use the center point; for nodes, use the node location
                if element.get("type") == "node":
                    elem_lat = element.get("lat")
                    elem_lon = element.get("lon")
                    if elem_lat is not None and elem_lon is not None:
                        distance = _calculate_distance(query_lat, query_lon, elem_lat, elem_lon)
                    else:
                        distance = float('inf')
                elif element.get("type") == "way":
                    # For ways, calculate center from nodes if available
                    nodes = element.get("nodes", [])
                    if nodes and "lat" in element:
                        # Overpass returns lat/lon for ways with "out body"
                        elem_lat = element.get("lat")
                        elem_lon = element.get("lon")
                        if elem_lat is not None and elem_lon is not None:
                            distance = _calculate_distance(query_lat, query_lon, elem_lat, elem_lon)
                        else:
                            # If no center provided, estimate using bounding box center
                            bounds = element.get("bounds", {})
                            if bounds:
                                center_lat = (bounds.get("minlat", 0) + bounds.get("maxlat", 0)) / 2
                                center_lon = (bounds.get("minlon", 0) + bounds.get("maxlon", 0)) / 2
                                distance = _calculate_distance(query_lat, query_lon, center_lat, center_lon)
                            else:
                                distance = float('inf')
                    else:
                        distance = float('inf')
                else:
                    distance = float('inf')

                roads_with_distance.append({
                    "speed_limit": speed_value,
                    "road_name": road_name,
                    "unit": unit,
                    "distance": distance if distance != float('inf') else None,
                })

        # If no roads found with speed limits
        if not roads_with_distance:
            return {
                "speed_limit": None,
                "road_name": None,
                "unit": None,
                "distance": None,
            }

        # Sort by distance and return the closest road
        roads_with_distance.sort(key=lambda x: x["distance"] if x["distance"] is not None else float('inf'))
        closest_road = roads_with_distance[0]

        _LOGGER.debug(
            "Found %d roads, closest is %sm away with speed limit %s %s",
            len(roads_with_distance),
            round(closest_road["distance"]) if closest_road["distance"] is not None else "unknown",
            closest_road["speed_limit"],
            closest_road["unit"]
        )

        return closest_road

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
                speed = int(round(float(maxspeed.replace("mph", "").strip())))
                return speed, "mph"
            elif "km/h" in maxspeed or "kmh" in maxspeed:
                speed = int(round(float(
                    maxspeed.replace("km/h", "").replace("kmh", "").strip()
                )))
                return speed, "km/h"
            else:
                # No unit specified, assume user preference
                speed = int(round(float(maxspeed)))
                return speed, self.unit_preference
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
    ) -> SpeedLimitData:
        """Query TomTom Search API (Reverse Geocoding) for speed limit data."""
        import aiohttp
        import async_timeout

        if not self.api_key:
            raise ValueError("TomTom API key not configured")

        # Construct URL: base_url/{lat},{lon}.json
        url = f"{TOMTOM_API_URL}/{latitude},{longitude}.json"
        
        params = {
            "key": self.api_key,
            "returnSpeedLimit": "true",
            "radius": 50,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(10):
                    async with session.get(url, params=params) as response:
                        if response.status == 403:
                            raise aiohttp.ClientError("TomTom API key is invalid or expired")
                        if response.status != 200:
                            raise aiohttp.ClientError(
                                f"TomTom API returned status {response.status}"
                            )

                        data = await response.json()
                        return self._parse_tomtom_response(data)
        except asyncio.TimeoutError as err:
            _LOGGER.debug("TomTom API request timed out: %s", err)
            raise

    def _parse_tomtom_response(self, data: dict[str, Any]) -> SpeedLimitData:
        """Parse TomTom Reverse Geocoding response."""
        try:
            addresses = data.get("addresses", [])
            
            if not addresses:
                return {
                    "speed_limit": None,
                    "road_name": None,
                    "unit": "km/h",
                    "distance": None,
                }

            # Get best match
            match = addresses[0]
            address_data = match.get("address", {})
            
            # Extract speed limit string (e.g. "50.00MPH" or "80.00km/h")
            speed_limit_str = address_data.get("speedLimit")
            
            speed_val = None
            unit = "km/h" # Default
            
            if speed_limit_str:
                # Basic parsing
                upper_str = speed_limit_str.upper()
                if "MPH" in upper_str:
                    try:
                        speed_val = int(round(float(upper_str.replace("MPH", "").strip())))
                        unit = "mph"
                    except ValueError:
                        pass
                elif "KM" in upper_str:
                    try:
                        # Handle km/h, kmh, etc.
                        clean_str = upper_str.replace("KM/H", "").replace("KMH", "").strip()
                        speed_val = int(round(float(clean_str)))
                        unit = "km/h"
                    except ValueError:
                        pass

            # Get road name
            road_name = address_data.get("street")
            if not road_name:
                # Try route numbers if street name is missing
                route_numbers = address_data.get("routeNumbers", [])
                if route_numbers:
                    road_name = ", ".join(route_numbers)

            return {
                "speed_limit": speed_val,
                "road_name": road_name,
                "unit": unit,
                "distance": 0.0,
            }
        except (KeyError, TypeError) as err:
            _LOGGER.warning("Could not parse TomTom response: %s", err)
            return {
                "speed_limit": None,
                "road_name": None,
                "unit": "km/h",
                "distance": None,
            }


class HERESpeedLimitProvider(BaseSpeedLimitProvider):
    """HERE Maps speed limit provider."""

    def get_provider_name(self) -> str:
        """Return the display name of this provider."""
        return DATA_SOURCE_NAMES[DATA_SOURCE_HERE]

    async def fetch_speed_limit(
        self, latitude: float, longitude: float
    ) -> SpeedLimitData:
        """Query HERE Geocoding & Search API v7 for speed limit data."""
        import aiohttp
        import async_timeout

        if not self.api_key:
            raise ValueError("HERE API key not configured")

        params = {
            "at": f"{latitude},{longitude}",
            "apiKey": self.api_key,
            "showNavAttributes": "speedLimits",  # Request explicit speed limits
            "show": "tz",  # Request timezone info
            "lang": "en-US",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with async_timeout.timeout(10):
                    async with session.get(HERE_API_URL, params=params) as response:
                        if response.status == 401 or response.status == 403:
                            raise aiohttp.ClientError("HERE API key is invalid or expired")
                        if response.status != 200:
                            raise aiohttp.ClientError(f"HERE API returned status {response.status}")

                        data = await response.json()
                        return self._parse_here_response(data)
        except asyncio.TimeoutError as err:
            _LOGGER.debug("HERE API request timed out: %s", err)
            raise

    def _parse_here_response(self, data: dict[str, Any]) -> SpeedLimitData:
        """Parse HERE response and extract speed limit."""
        try:
            items = data.get("items", [])

            if not items:
                _LOGGER.debug("No address data found in HERE response")
                return {
                    "speed_limit": None,
                    "road_name": None,
                    "unit": "km/h",
                    "distance": None,
                }

            # Get first result
            first_item = items[0]
            
            # Extract road name
            # HERE v7 returns 'title' (full address) and address components
            address = first_item.get("address", {})
            road_name = address.get("street")
            if not road_name:
                road_name = first_item.get("title")

            # Extract timezone
            timezone = None
            tz_info = first_item.get("timeZone")
            if tz_info:
                timezone = tz_info.get("name")

            # Extract speed limit from navigationAttributes
            nav_attrs = first_item.get("navigationAttributes", {})
            speed_limits = nav_attrs.get("speedLimits", [])
            
            speed_val = None
            unit = "km/h" # Default

            if speed_limits:
                # Use the first speed limit found (usually matched to the road)
                # In complex scenarios there might be "to" and "from" directions,
                # but for a point query, the first valid one is usually correct.
                limit_data = speed_limits[0]
                max_speed = limit_data.get("maxSpeed")
                
                # Check unit
                # HERE returns 'mph' or 'km/h' in speedUnit
                src_unit = limit_data.get("speedUnit", "km/h")
                
                if max_speed is not None:
                    # Convert float to int with rounding (e.g. 50.0 -> 50)
                    try:
                        speed_val = int(round(float(max_speed)))
                    except (ValueError, TypeError):
                        speed_val = None
                    
                    unit = "mph" if src_unit == "mph" else "km/h"

            return {
                "speed_limit": speed_val,
                "road_name": road_name,
                "unit": unit,
                "distance": 0.0,
                "timezone": timezone,
            }
        except (KeyError, TypeError, IndexError) as err:
            _LOGGER.warning("Could not parse HERE response: %s", err)
            return {
                "speed_limit": None,
                "road_name": None,
                "unit": "km/h",
                "distance": None,
            }
