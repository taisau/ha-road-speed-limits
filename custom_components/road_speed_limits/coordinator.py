"""DataUpdateCoordinator for Road Speed Limits."""
import asyncio
from datetime import timedelta
import logging
import time
import math

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CACHE_SPEED_THRESHOLD,
    DATA_SOURCE_HERE,
    DATA_SOURCE_OSM,
    DATA_SOURCE_TOMTOM,
    DEFAULT_UNIT,
    DEFAULT_MIN_UPDATE_DISTANCE,
    DOMAIN,
    SpeedLimitData,
)
from .helpers import convert_speed, get_coordinate_from_entity, validate_coordinates
from .providers import (
    BaseSpeedLimitProvider,
    HERESpeedLimitProvider,
    OSMSpeedLimitProvider,
    TomTomSpeedLimitProvider,
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


class RoadSpeedLimitsCoordinator(DataUpdateCoordinator):
    """Class to manage fetching speed limit data from multiple sources."""

    def __init__(
        self,
        hass: HomeAssistant,
        latitude: float,
        longitude: float,
        data_source: str = DATA_SOURCE_OSM,
        unit_preference: str = DEFAULT_UNIT,
        min_update_distance: int = DEFAULT_MIN_UPDATE_DISTANCE,
        speed_entity_id: str | None = None,
        tomtom_api_key: str | None = None,
        here_api_key: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        # Disable automatic polling by setting update_interval to None
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,
        )
        self.latitude = latitude
        self.longitude = longitude
        
        # Track last API fetch location to calculate distance
        self._last_api_latitude = latitude
        self._last_api_longitude = longitude

        self.data_source = data_source
        self.unit_preference = unit_preference
        self.min_update_distance = min_update_distance
        self.fallback_active = False
        self.active_provider_name = None
        self.speed_entity_id = speed_entity_id
        
        self.lat_entity_id = None
        self.lon_entity_id = None
        self._unsub_listeners = []

        # Initialize cache for location-based data
        # Cache is only used when speed < 10 mph to avoid stale data at highway speeds
        self._cache: dict[str, tuple[dict[str, SpeedLimitData], float]] = {}
        self._cache_ttl = 300  # 5 minutes in seconds

        # Initialize providers dict
        self.providers: dict[str, BaseSpeedLimitProvider] = {}

        # Always add OSM with unit preference for smart defaults
        self.providers[DATA_SOURCE_OSM] = OSMSpeedLimitProvider(unit_preference=unit_preference)

        # Add TomTom if key is present
        if tomtom_api_key:
            self.providers[DATA_SOURCE_TOMTOM] = TomTomSpeedLimitProvider(tomtom_api_key)

        # Add HERE if key is present
        if here_api_key:
            self.providers[DATA_SOURCE_HERE] = HERESpeedLimitProvider(here_api_key)

    def setup_subscriptions(self, lat_entity_id: str, lon_entity_id: str) -> None:
        """Set up event listeners for coordinate and speed entities."""
        self.lat_entity_id = lat_entity_id
        self.lon_entity_id = lon_entity_id
        
        # Unsubscribe from previous listeners if any
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

        # Track latitude changes
        self._unsub_listeners.append(
            async_track_state_change_event(
                self.hass, [lat_entity_id], self._on_location_change
            )
        )

        # Track longitude changes
        self._unsub_listeners.append(
            async_track_state_change_event(
                self.hass, [lon_entity_id], self._on_location_change
            )
        )

        # Track speed changes
        if self.speed_entity_id:
            self._unsub_listeners.append(
                async_track_state_change_event(
                    self.hass, [self.speed_entity_id], self._on_speed_change
                )
            )
            
        _LOGGER.debug(
            "Subscribed to updates from lat=%s, lon=%s, speed=%s", 
            lat_entity_id, 
            lon_entity_id, 
            self.speed_entity_id
        )

    @callback
    def _on_location_change(self, event: Event) -> None:
        """Handle location entity state changes."""
        # Get current state of both entities
        lat_state = self.hass.states.get(self.lat_entity_id)
        lon_state = self.hass.states.get(self.lon_entity_id)

        # Extract coordinates
        new_lat = get_coordinate_from_entity(lat_state, "latitude")
        new_lon = get_coordinate_from_entity(lon_state, "longitude")

        # Validate coordinates
        if not validate_coordinates(new_lat, new_lon):
            return

        # Calculate distance moved since last API update
        distance = _calculate_distance(
            self._last_api_latitude, 
            self._last_api_longitude, 
            new_lat, 
            new_lon
        )

        # Check if moved enough to trigger update
        if distance >= self.min_update_distance:
            _LOGGER.debug(
                "Moved %.1f meters (>= %s), triggering update", 
                distance, 
                self.min_update_distance
            )
            self.latitude = new_lat
            self.longitude = new_lon
            # This triggers _async_update_data
            self.hass.async_create_task(self.async_request_refresh())
        else:
            # Update internal coordinates but don't trigger refresh yet
            self.latitude = new_lat
            self.longitude = new_lon

    @callback
    def _on_speed_change(self, event: Event) -> None:
        """Handle speed entity state changes."""
        # We generally don't trigger updates purely on speed change,
        # unless we want to invalidate cache or something.
        # For now, we just log it or use it to decide if we should force an update 
        # (e.g. if we were stationary and now moving fast).
        
        # Optimization: If we just started moving, maybe trigger a refresh if the last one was cached?
        # But _async_update_data checks current speed anyway.
        pass

    def _get_cache_key(self, lat: float, lon: float) -> str:
        """Generate cache key from rounded coordinates.

        Uses 4 decimal places (~11m precision) for cache key.
        """
        return f"{round(lat, 4)}_{round(lon, 4)}"

    def _get_cached_data(self, lat: float, lon: float) -> dict[str, SpeedLimitData] | None:
        """Get cached data if valid.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Cached data if valid, None otherwise
        """
        key = self._get_cache_key(lat, lon)
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return data
            # Cache expired, remove it
            del self._cache[key]
        return None

    def _set_cached_data(self, lat: float, lon: float, data: dict[str, SpeedLimitData]) -> None:
        """Store data in cache.

        Args:
            lat: Latitude
            lon: Longitude
            data: Data to cache
        """
        key = self._get_cache_key(lat, lon)
        self._cache[key] = (data, time.time())

    async def _async_update_data(self) -> dict[str, SpeedLimitData]:
        """Fetch speed limit data with optimized provider query.

        Strategy:
        1. Check cache first (only if speed < 10 mph)
        2. Query primary provider
        3. If primary succeeds with data, we're done
        4. If primary fails/no data, try configured fallbacks sequentially

        Returns:
            Dictionary mapping provider names to their data
        """
        # Update last API location tracking
        self._last_api_latitude = self.latitude
        self._last_api_longitude = self.longitude

        # Check cache only if speed is below threshold (< 10 mph)
        # This prevents using stale cached data when moving at speed
        use_cache = True
        if self.speed_entity_id:
            speed_state = self.hass.states.get(self.speed_entity_id)
            if speed_state and speed_state.state not in ("unavailable", "unknown"):
                try:
                    speed_kmh = float(speed_state.state)
                    if speed_kmh >= CACHE_SPEED_THRESHOLD:
                        use_cache = False
                        _LOGGER.debug("Speed %.1f km/h >= threshold, bypassing cache", speed_kmh)
                except (ValueError, TypeError):
                    pass  # If we can't parse speed, allow cache

        if use_cache:
            cached = self._get_cached_data(self.latitude, self.longitude)
            if cached:
                _LOGGER.debug("Using cached data for location")
                return cached

        results = {}

        # 1. Try primary provider first
        try:
            primary_data = await self.hass.async_create_task(
                self.providers[self.data_source].fetch_speed_limit(
                    self.latitude, self.longitude
                )
            )
            results[self.data_source] = self._apply_unit_conversion(primary_data)
        except Exception as err:
            _LOGGER.debug("Primary provider %s failed: %s", self.data_source, err)
            results[self.data_source] = None

        # 2. If primary succeeded with data, we're done
        primary_result = results.get(self.data_source)
        if primary_result and primary_result.get("speed_limit") is not None:
            self.fallback_active = False
            self.active_provider_name = self.providers[self.data_source].get_provider_name()
            self._set_cached_data(self.latitude, self.longitude, results)
            return results

        # 3. Primary failed or returned no data - try configured fallbacks
        _LOGGER.debug("Primary provider %s has no data, trying fallbacks", self.data_source)
        self.fallback_active = True

        # Build fallback order from configured providers (Issue 4)
        # Preferred order: HERE -> TomTom -> OSM
        fallback_order = [DATA_SOURCE_HERE, DATA_SOURCE_TOMTOM, DATA_SOURCE_OSM]
        available_fallbacks = [
            source for source in fallback_order
            if source in self.providers and source != self.data_source
        ]

        # Query fallbacks sequentially until one succeeds
        for fallback_source in available_fallbacks:
            try:
                fallback_data = await self.hass.async_create_task(
                    self.providers[fallback_source].fetch_speed_limit(
                        self.latitude, self.longitude
                    )
                )
                results[fallback_source] = self._apply_unit_conversion(fallback_data)

                # If this fallback has data, we're done
                if results[fallback_source] and results[fallback_source].get("speed_limit") is not None:
                    self.active_provider_name = self.providers[fallback_source].get_provider_name()
                    _LOGGER.info("Using fallback provider %s", fallback_source)
                    break
            except Exception as err:
                _LOGGER.debug("Fallback provider %s failed: %s", fallback_source, err)
                results[fallback_source] = None

        self._set_cached_data(self.latitude, self.longitude, results)
        return results

    def get_primary_data(self) -> SpeedLimitData | None:
        """Get data for the configured primary provider with multi-stage fallback.

        Returns:
            Speed limit data from the active provider, or None if no data available
        """
        # 1. Try selected primary source
        primary_res = self.data.get(self.data_source)
        if primary_res and primary_res.get("speed_limit") is not None:
            return primary_res

        # Define fallback order: HERE -> TomTom -> OSM
        fallback_order = [DATA_SOURCE_HERE, DATA_SOURCE_TOMTOM, DATA_SOURCE_OSM]

        for source in fallback_order:
            if source == self.data_source:
                continue  # Already tried as primary

            res = self.data.get(source)
            if res and res.get("speed_limit") is not None:
                # Found a working fallback with actual data
                if not self.fallback_active:
                    _LOGGER.info("Primary %s has no data, falling back to %s", self.data_source, source)
                    self.fallback_active = True

                # Update active provider name for attributes
                self.active_provider_name = self.providers[source].get_provider_name()
                return res

        return primary_res  # Return the primary (empty) result if all fallbacks fail

    def _apply_unit_conversion(self, data: SpeedLimitData) -> SpeedLimitData:
        """Apply unit conversion to fetched data based on user preference.

        Args:
            data: Raw data from provider

        Returns:
            Data with converted speed limit and corrected unit
        """
        if not data or data.get("speed_limit") is None:
            return data

        # Create a copy to avoid mutating original
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
