# Road Speed Limits for Home Assistant

A Home Assistant custom integration that displays current road speed limits based on GPS coordinates using multiple data sources including OpenStreetMap, TomTom, and HERE Maps.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

## Features

- **Multiple Data Sources**: Choose between OpenStreetMap (free), TomTom, or HERE Maps for speed limit data
- **Automatic Fallback**: If your selected provider fails, the integration automatically falls back to OpenStreetMap
- **Real-time Speed Limit Detection**: Automatically fetches speed limit information from your chosen provider
- **Flexible Location Input**: Use any Home Assistant entity that provides latitude and longitude coordinates
- **Easy Configuration**: Simple UI-based setup through Home Assistant's integration page
- **Automatic Updates**: Polls for speed limit changes every 5 minutes
- **Rich Attributes**: Includes road name, coordinates, data source, active provider, fallback status, and last update time

## Installation

### Via HACS (Recommended)

1. Open HACS in your Home Assistant instance
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add the URL: `https://github.com/yourusername/ha-road-speed-limits`
6. Select category: "Integration"
7. Click "Add"
8. Find "Road Speed Limits" in the integration list and click "Install"
9. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/road_speed_limits` folder from this repository
2. Copy it to your Home Assistant's `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

### API Keys Setup (Optional)

If you want to use TomTom or HERE Maps as your data source, you need to configure API keys in your `secrets.yaml` file.

#### Getting API Keys

**TomTom API Key:**
1. Go to [TomTom Developer Portal](https://developer.tomtom.com/)
2. Create a free account
3. Create a new app and enable the "Traffic API"
4. Copy your API key
5. Free tier includes 2,500 requests per day

**HERE API Key:**
1. Go to [HERE Developer Portal](https://developer.here.com/)
2. Create a free account
3. Create a new project and generate an API key
4. Enable the "Traffic API v7"
5. Copy your API key
6. Free tier includes 250,000 requests per month

#### Add API Keys to secrets.yaml

Edit your `secrets.yaml` file (in your Home Assistant config directory) and add:

```yaml
tomtom_api_key: "your_tomtom_api_key_here"
here_api_key: "your_here_api_key_here"
```

**Note**: Only add the keys for the services you plan to use. OpenStreetMap requires no API key.

### Integration Setup

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Road Speed Limits"
4. Select the integration
5. Provide the following information:
   - **Latitude Entity**: Entity that provides latitude coordinate
   - **Longitude Entity**: Entity that provides longitude coordinate
   - **Data Source**: Choose from:
     - **OpenStreetMap** (default, free, no API key required)
     - **TomTom** (requires API key in secrets.yaml)
     - **HERE Maps** (requires API key in secrets.yaml)
6. Click **Submit**

The integration will create a sensor entity named `sensor.road_speed_limit` that displays the current speed limit.

#### Supported GPS Entity Formats

The integration supports multiple GPS entity formats:

**Option 1: Single GPS Sensor with Attributes** (Recommended)
```yaml
# Use the SAME entity for both latitude and longitude
sensor.pepwave_gps_data:
  state: "45.365097,-123.968731"
  attributes:
    latitude: 45.365097
    longitude: -123.968731
```
→ Select `sensor.pepwave_gps_data` for **both** Latitude Entity and Longitude Entity

**Option 2: Device Tracker / Person Entities**
```yaml
device_tracker.phone:
  state: "home"
  attributes:
    latitude: 45.365097
    longitude: -123.968731
```
→ Select `device_tracker.phone` for **both** Latitude Entity and Longitude Entity

**Option 3: Separate Sensor Entities**
```yaml
sensor.gps_latitude:
  state: "45.365097"

sensor.gps_longitude:
  state: "-123.968731"
```
→ Select `sensor.gps_latitude` for Latitude Entity and `sensor.gps_longitude` for Longitude Entity

**The integration automatically detects which format your entities use** and extracts coordinates accordingly.

### Changing Data Source

You can change the data source after setup:

1. Go to **Settings** → **Devices & Services**
2. Find the "Road Speed Limits" integration
3. Click **Configure**
4. Select a different data source
5. Click **Submit**

The integration will reload and start using the new data source on the next update.

## Usage

The sensor will display the speed limit as its state (e.g., `50`) with the unit (e.g., `km/h` or `mph`).

### Sensor Attributes

The sensor provides the following attributes:

- `latitude`: Current latitude coordinate
- `longitude`: Current longitude coordinate
- `road_name`: Name of the road (if available from the data source)
- `data_source`: Selected data source (OpenStreetMap, TomTom, or HERE Maps)
- `active_provider`: Currently active provider (may differ from selected if fallback is active)
- `fallback_active`: Whether the integration is currently using fallback mode (true/false)
- `last_update`: Timestamp of last update

### Example Automation

```yaml
automation:
  - alias: "Speed Warning"
    trigger:
      - platform: numeric_state
        entity_id: sensor.car_speed
        above: sensor.road_speed_limit
    action:
      - service: notify.mobile_app
        data:
          message: "You are exceeding the speed limit!"
```

### Lovelace Card Example

```yaml
type: entities
entities:
  - entity: sensor.road_speed_limit
    name: Current Speed Limit
```

## Data Sources

The integration supports three data sources for speed limit information:

### OpenStreetMap (Free)

OpenStreetMap's Overpass API provides community-maintained speed limit data worldwide.

- **Cost**: Free, no API key required
- **Coverage**: Varies by region. Urban areas typically have better coverage
- **Rate Limit**: None (fair use expected)
- **Accuracy**: Community-maintained, may be outdated in some areas
- **Best for**: General use, testing, or areas with good OSM coverage

### TomTom

TomTom's Traffic API provides commercial-grade speed limit data.

- **Cost**: Free tier includes 2,500 requests per day
- **Coverage**: Excellent worldwide coverage
- **Rate Limit**: 2,500 requests/day (free tier)
- **Accuracy**: High-quality commercial data
- **Best for**: Users needing reliable, up-to-date data with moderate usage
- **Setup**: Requires API key in secrets.yaml

### HERE Maps

HERE's Flow API provides enterprise-grade traffic and speed limit data.

- **Cost**: Free tier includes 250,000 requests per month
- **Coverage**: Excellent worldwide coverage
- **Rate Limit**: 250,000 requests/month (free tier)
- **Accuracy**: High-quality commercial data
- **Best for**: Heavy users or applications requiring maximum reliability
- **Setup**: Requires API key in secrets.yaml

### Comparison Table

| Feature | OpenStreetMap | TomTom | HERE Maps |
|---------|---------------|---------|-----------|
| API Key Required | No | Yes | Yes |
| Free Tier | Unlimited* | 2,500/day | 250,000/month |
| Coverage | Good | Excellent | Excellent |
| Accuracy | Community | Commercial | Commercial |
| Updates | Community | Real-time | Real-time |

*Fair use policy applies

### Automatic Fallback

If your selected data source (TomTom or HERE Maps) fails for any reason, the integration automatically falls back to OpenStreetMap to ensure continuous operation.

**Fallback scenarios:**
- API key is missing or invalid
- Rate limit exceeded
- Network errors or timeouts
- Service unavailable

When fallback is active:
- The `active_provider` attribute will show "OpenStreetMap"
- The `fallback_active` attribute will be `true`
- A warning will be logged in Home Assistant logs
- The integration will automatically retry the primary provider on the next update

**Note**: Fallback only occurs for TomTom and HERE Maps. If OpenStreetMap (your primary source) fails, no fallback is available.

## Troubleshooting

### No Speed Limit Data

If the sensor shows "Unknown" or no data:

1. Verify your latitude and longitude entities are providing valid coordinates
2. Check the `active_provider` attribute to see which data source is being used
3. If using OpenStreetMap, verify the road has speed limit data at [openstreetmap.org](https://www.openstreetmap.org)
4. The integration searches within 50 meters of the coordinates
5. Wait for the next update cycle (5 minutes)
6. Check Home Assistant logs for errors

### Entity Not Found Error

Make sure the latitude and longitude entity IDs you provided actually exist in your Home Assistant instance. You can check this in **Developer Tools** → **States**.

### Invalid Coordinates Error

If you get an error about invalid coordinates during setup:

1. Check your entity in **Developer Tools** → **States**
2. Verify the entity has either:
   - `latitude` and `longitude` attributes (most GPS sensors, device trackers, person entities)
   - A numeric state value between -90 to 90 for latitude or -180 to 180 for longitude
3. Common formats that work:
   - GPS sensor with attributes: `sensor.pepwave_gps_data` (use for both lat and lon)
   - Device tracker: `device_tracker.phone` (use for both lat and lon)
   - Separate sensors: `sensor.latitude` and `sensor.longitude`
4. The integration will tell you what values it found if validation fails

### API Key Issues

If you selected TomTom or HERE Maps but it's not working:

1. Check that you added the correct API key to `secrets.yaml`:
   - Key name must be exactly `tomtom_api_key` or `here_api_key`
   - Ensure the key is quoted: `tomtom_api_key: "your_key_here"`
2. Restart Home Assistant after adding API keys to secrets.yaml
3. Check Home Assistant logs for authentication errors
4. Verify your API key is valid on the provider's website
5. Check if you've exceeded your rate limit
6. The integration will automatically fall back to OpenStreetMap if the API key is invalid

### Fallback Mode

If the `fallback_active` attribute is `true`:

1. Check Home Assistant logs to see why the primary provider failed
2. Common causes:
   - Missing or invalid API key
   - Rate limit exceeded
   - Network connectivity issues
   - Provider service outage
3. The integration will automatically retry your selected provider on the next update
4. If fallback persists, consider switching to a different data source or using OpenStreetMap

### Checking Logs

To view detailed logs:

1. Go to **Settings** → **System** → **Logs**
2. Search for "road_speed_limits"
3. Look for warnings or errors related to data fetching or API calls

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Attribution

This integration can use data from multiple sources:

- **OpenStreetMap**: Data from [OpenStreetMap](https://www.openstreetmap.org/copyright), made available under the Open Database License (ODbL)
- **TomTom**: Speed limit data from [TomTom Traffic API](https://developer.tomtom.com/)
- **HERE Maps**: Speed limit data from [HERE Flow API](https://developer.here.com/)

Please ensure you comply with the terms of service of any data provider you use.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
