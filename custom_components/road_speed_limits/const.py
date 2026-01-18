"""Constants for the Road Speed Limits integration."""
from datetime import timedelta

DOMAIN = "road_speed_limits"

# Configuration keys
CONF_LATITUDE_ENTITY = "latitude_entity"
CONF_LONGITUDE_ENTITY = "longitude_entity"

# Update interval
UPDATE_INTERVAL = timedelta(minutes=5)

# OpenStreetMap Overpass API
OSM_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OSM_SEARCH_RADIUS = 50  # meters

# Sensor attributes
ATTR_LATITUDE = "latitude"
ATTR_LONGITUDE = "longitude"
ATTR_ROAD_NAME = "road_name"
ATTR_DATA_SOURCE = "data_source"
ATTR_LAST_UPDATE = "last_update"

# Default values
DEFAULT_NAME = "Road Speed Limit"
DATA_SOURCE_OSM = "OpenStreetMap"
