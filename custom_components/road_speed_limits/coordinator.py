"""DataUpdateCoordinator for Road Speed Limits."""
import asyncio
from datetime import timedelta
import logging
import time
import math

from homeassistant.core import HomeAssistant, Event, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CACHE_SPEED_THRESHOLD,
    DATA_SOURCE_HERE,
    DATA_SOURCE_OSM,
    DATA_SOURCE_TOMTOM,
    DEFAULT_UNIT,
    DEFAULT_MIN_UPDATE_DISTANCE,
    DEFAULT_MIN_UPDATE_TIME,
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
    """Calculate Haversine distance in meters between two points."""
    R = 6371000
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
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
        min_update_time: int = DEFAULT_MIN_UPDATE_TIME,
        speed_entity_id: str | None = None,
        tomtom_api_key: str | None = None,
        here_api_key: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,
        )
        self.latitude = latitude
        self.longitude = longitude
        self._last_api_latitude = latitude
        self._last_api_longitude = longitude

        self.data_source = data_source
        self.unit_preference = unit_preference
        self.min_update_distance = min_update_distance
        self.min_update_time = min_update_time
        
        # Polling state
        self.polling_active = False
        self._last_active_time = time.time()
        self._poll_remove_callback = None

        self.fallback_active = False
        self.active_provider_name = None
        self.speed_entity_id = speed_entity_id
        
        self.lat_entity_id = None
        self.lon_entity_id = None
        self._unsub_listeners = []

        self._cache: dict[str, tuple[dict[str, SpeedLimitData], float]] = {}
        self._cache_ttl = 300

        self.providers: dict[str, BaseSpeedLimitProvider] = {}
        self.providers[DATA_SOURCE_OSM] = OSMSpeedLimitProvider(unit_preference=unit_preference)

        if tomtom_api_key:
            self.providers[DATA_SOURCE_TOMTOM] = TomTomSpeedLimitProvider(tomtom_api_key)

        if here_api_key:
            self.providers[DATA_SOURCE_HERE] = HERESpeedLimitProvider(here_api_key)

    def setup_subscriptions(self, lat_entity_id: str, lon_entity_id: str) -> None:
        """Set up event listeners for coordinate and speed entities."""
        self.lat_entity_id = lat_entity_id
        self.lon_entity_id = lon_entity_id
        
        for unsub in self._unsub_listeners:
            unsub()
        self._unsub_listeners.clear()

        self._unsub_listeners.append(
            async_track_state_change_event(
                self.hass, [lat_entity_id], self._on_location_change
            )
        )

        self._unsub_listeners.append(
            async_track_state_change_event(
                self.hass, [lon_entity_id], self._on_location_change
            )
        )

        if self.speed_entity_id:
            self._unsub_listeners.append(
                async_track_state_change_event(
                    self.hass, [self.speed_entity_id], self._on_speed_change
                )
            )

    def _start_polling(self) -> None:
        """Start the high-frequency polling loop."""
        self._last_active_time = time.time()
        
        if self.polling_active:
            return

        self.polling_active = True
        _LOGGER.debug("Starting 1s polling loop")
        
        # Immediately trigger update
        self.hass.async_create_task(self.async_request_refresh())
        
        # Start 1s timer
        self._poll_remove_callback = async_track_time_interval(
            self.hass, self._poll_interval, timedelta(seconds=1)
        )
        self.async_update_listeners()

    def _stop_polling(self) -> None:
        """Stop the polling loop."""
        if not self.polling_active:
            return

        if self._poll_remove_callback:
            self._poll_remove_callback()
            self._poll_remove_callback = None
        
        self.polling_active = False
        _LOGGER.debug("Stopping polling loop (timeout > %s s)", self.min_update_time)
        self.async_update_listeners()

    @callback
    def _poll_interval(self, now) -> None:
        """Called every second when polling is active."""
        # Check for timeout
        if time.time() - self._last_active_time > self.min_update_time:
            self._stop_polling()
            return

        # Request data refresh
        self.hass.async_create_task(self.async_request_refresh())

    @callback
    def _on_location_change(self, event: Event) -> None:
        """Handle location entity state changes."""
        lat_state = self.hass.states.get(self.lat_entity_id)
        lon_state = self.hass.states.get(self.lon_entity_id)

        new_lat = get_coordinate_from_entity(lat_state, "latitude")
        new_lon = get_coordinate_from_entity(lon_state, "longitude")

        if not validate_coordinates(new_lat, new_lon):
            return

        # Update current coordinates immediately
        self.latitude = new_lat
        self.longitude = new_lon

        distance = _calculate_distance(
            self._last_api_latitude, 
            self._last_api_longitude, 
            new_lat, 
            new_lon
        )

        if distance >= self.min_update_distance:
            _LOGGER.debug(
                "Moved %.1f meters (>= %s), resetting idle timer", 
                distance, 
                self.min_update_distance
            )
            # Wake up / Keep awake
            self._start_polling()

    @callback
    def _on_speed_change(self, event: Event) -> None:
        """Handle speed entity state changes."""
        pass

    def _get_cache_key(self, lat: float, lon: float) -> str:
        return f"{round(lat, 4)}_{round(lon, 4)}"

    def _get_cached_data(self, lat: float, lon: float) -> dict[str, SpeedLimitData] | None:
        key = self._get_cache_key(lat, lon)
        if key in self._cache:
            data, timestamp = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return data
            del self._cache[key]
        return None

    def _set_cached_data(self, lat: float, lon: float, data: dict[str, SpeedLimitData]) -> None:
        key = self._get_cache_key(lat, lon)
        self._cache[key] = (data, time.time())

    async def _async_update_data(self) -> dict[str, SpeedLimitData]:
        """Fetch speed limit data."""
        # Update tracking
        self._last_api_latitude = self.latitude
        self._last_api_longitude = self.longitude

        use_cache = True
        if self.speed_entity_id:
            speed_state = self.hass.states.get(self.speed_entity_id)
            if speed_state and speed_state.state not in ("unavailable", "unknown"):
                try:
                    speed_kmh = float(speed_state.state)
                    if speed_kmh >= CACHE_SPEED_THRESHOLD:
                        use_cache = False
                except (ValueError, TypeError):
                    pass

        if use_cache:
            cached = self._get_cached_data(self.latitude, self.longitude)
            if cached:
                return cached

        results = {}
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

        primary_result = results.get(self.data_source)
        if primary_result and primary_result.get("speed_limit") is not None:
            self.fallback_active = False
            self.active_provider_name = self.providers[self.data_source].get_provider_name()
            self._set_cached_data(self.latitude, self.longitude, results)
            return results

        self.fallback_active = True
        fallback_order = [DATA_SOURCE_HERE, DATA_SOURCE_TOMTOM, DATA_SOURCE_OSM]
        available_fallbacks = [
            source for source in fallback_order
            if source in self.providers and source != self.data_source
        ]

        for fallback_source in available_fallbacks:
            try:
                fallback_data = await self.hass.async_create_task(
                    self.providers[fallback_source].fetch_speed_limit(
                        self.latitude, self.longitude
                    )
                )
                results[fallback_source] = self._apply_unit_conversion(fallback_data)

                if results[fallback_source] and results[fallback_source].get("speed_limit") is not None:
                    self.active_provider_name = self.providers[fallback_source].get_provider_name()
                    break
            except Exception:
                results[fallback_source] = None

        self._set_cached_data(self.latitude, self.longitude, results)
        return results

    def get_primary_data(self) -> SpeedLimitData | None:
        primary_res = self.data.get(self.data_source)
        if primary_res and primary_res.get("speed_limit") is not None:
            return primary_res

        fallback_order = [DATA_SOURCE_HERE, DATA_SOURCE_TOMTOM, DATA_SOURCE_OSM]
        for source in fallback_order:
            if source == self.data_source:
                continue

            res = self.data.get(source)
            if res and res.get("speed_limit") is not None:
                if not self.fallback_active:
                    self.fallback_active = True
                self.active_provider_name = self.providers[source].get_provider_name()
                return res

        return primary_res

    def _apply_unit_conversion(self, data: SpeedLimitData) -> SpeedLimitData:
        if not data or data.get("speed_limit") is None:
            return data
        data = data.copy()
        source_unit = data.get("unit")
        if source_unit and source_unit != self.unit_preference:
            data["speed_limit"] = convert_speed(
                data["speed_limit"], source_unit, self.unit_preference
            )
            data["unit"] = self.unit_preference
        return data