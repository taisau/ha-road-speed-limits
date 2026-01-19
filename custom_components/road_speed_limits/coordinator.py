"""DataUpdateCoordinator for Road Speed Limits."""
import asyncio
from datetime import timedelta
import logging
import time

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CACHE_SPEED_THRESHOLD,
    DATA_SOURCE_HERE,
    DATA_SOURCE_OSM,
    DATA_SOURCE_TOMTOM,
    DEFAULT_UNIT,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    SpeedLimitData,
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
        update_interval: timedelta | None = None,
        speed_entity_id: str | None = None,
        tomtom_api_key: str | None = None,
        here_api_key: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        if update_interval is None:
            update_interval = timedelta(minutes=DEFAULT_UPDATE_INTERVAL)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.latitude = latitude
        self.longitude = longitude
        self.data_source = data_source
        self.unit_preference = unit_preference
        self.fallback_active = False
        self.active_provider_name = None
        self.speed_entity_id = speed_entity_id

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
        _LOGGER.warning("Primary provider %s has no data, trying fallbacks", self.data_source)
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

    def update_location(self, latitude: float, longitude: float) -> None:
        """Update the coordinates to search."""
        self.latitude = latitude
        self.longitude = longitude
