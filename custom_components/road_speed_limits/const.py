"""Constants for the Road Speed Limits integration."""
from datetime import timedelta
from typing import TypedDict


class SpeedLimitData(TypedDict, total=False):
    """Speed limit data structure returned by providers."""
    speed_limit: int | None
    road_name: str | None
    unit: str
    distance: float | None  # Distance in meters to the road


DOMAIN = "road_speed_limits"

# Configuration keys
CONF_LATITUDE_ENTITY = "latitude_entity"
CONF_LONGITUDE_ENTITY = "longitude_entity"
CONF_DATA_SOURCE = "data_source"
CONF_UNIT = "unit"
CONF_SPEED_ENTITY = "speed_entity"
CONF_MIN_UPDATE_DISTANCE = "min_update_distance"
CONF_MIN_UPDATE_TIME = "min_update_time"
CONF_TOMTOM_API_KEY = "tomtom_api_key"
CONF_HERE_API_KEY = "here_api_key"

# Default values
DEFAULT_SPEED_ENTITY = "sensor.vehicle_speed"
DEFAULT_MIN_UPDATE_DISTANCE = 20  # meters
DEFAULT_MIN_UPDATE_TIME = 60  # seconds

# Cache threshold (speed in km/h below which cache is used)
# Set to 10 mph (16 km/h) - cache only helps when nearly stationary
CACHE_SPEED_THRESHOLD = 16  # km/h (≈10 mph)

# Data sources
DATA_SOURCE_OSM = "osm"
DATA_SOURCE_TOMTOM = "tomtom"
DATA_SOURCE_HERE = "here"

# Data source display names
DATA_SOURCE_NAMES = {
    DATA_SOURCE_OSM: "OpenStreetMap",
    DATA_SOURCE_TOMTOM: "TomTom",
    DATA_SOURCE_HERE: "HERE Maps",
}

# OpenStreetMap Overpass API
OSM_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSM_SEARCH_RADIUS = 50  # meters (reduced for better accuracy)

# TomTom API
TOMTOM_API_URL = "https://api.tomtom.com/search/2/reverseGeocode"

# HERE API
HERE_API_URL = "https://revgeocode.search.hereapi.com/v1/revgeocode"

# Sensor attributes
ATTR_LATITUDE = "latitude"
ATTR_LONGITUDE = "longitude"
ATTR_ROAD_NAME = "road_name"
ATTR_DATA_SOURCE = "data_source"
ATTR_ACTIVE_PROVIDER = "active_provider"
ATTR_FALLBACK_ACTIVE = "fallback_active"
ATTR_LAST_UPDATE = "last_update"

# Units
UNIT_KMH = "km/h"
UNIT_MPH = "mph"

# Unit display names
UNIT_NAMES = {
    UNIT_KMH: "Kilometers per hour (km/h)",
    UNIT_MPH: "Miles per hour (mph)",
}

DEFAULT_NAME = "Road Speed Limit"
DEFAULT_DATA_SOURCE = DATA_SOURCE_HERE
DEFAULT_UNIT = UNIT_MPH
