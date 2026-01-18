# Road Speed Limits for Home Assistant

A Home Assistant custom integration that displays current road speed limits based on GPS coordinates using OpenStreetMap data.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

## Features

- **Real-time Speed Limit Detection**: Automatically fetches speed limit information from OpenStreetMap
- **Flexible Location Input**: Use any Home Assistant entity that provides latitude and longitude coordinates
- **Easy Configuration**: Simple UI-based setup through Home Assistant's integration page
- **Automatic Updates**: Polls for speed limit changes every 5 minutes
- **Rich Attributes**: Includes road name, coordinates, data source, and last update time

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

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Road Speed Limits"
4. Select the integration
5. Provide the following information:
   - **Latitude Entity**: Entity ID that provides latitude (e.g., `sensor.latitude`, `device_tracker.phone`, `person.john`)
   - **Longitude Entity**: Entity ID that provides longitude (e.g., `sensor.longitude`, `device_tracker.phone`, `person.john`)
6. Click **Submit**

The integration will create a sensor entity named `sensor.road_speed_limit` that displays the current speed limit.

## Usage

The sensor will display the speed limit as its state (e.g., `50`) with the unit (e.g., `km/h` or `mph`).

### Sensor Attributes

The sensor provides the following attributes:

- `latitude`: Current latitude coordinate
- `longitude`: Current longitude coordinate
- `road_name`: Name of the road (if available)
- `data_source`: Data source (OpenStreetMap)
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

### OpenStreetMap (Current)

The integration currently uses OpenStreetMap's Overpass API to fetch speed limit data. This is a free, community-maintained service that provides speed limit information worldwide.

**Coverage**: Varies by region. Urban areas typically have better coverage.

### Future Data Sources

- HERE Maps (planned)
- TomTom (planned)

## Troubleshooting

### No Speed Limit Data

If the sensor shows "Unknown" or no data:

1. Verify your latitude and longitude entities are providing valid coordinates
2. Check if the road has speed limit data in OpenStreetMap (visit [openstreetmap.org](https://www.openstreetmap.org))
3. The integration searches within 50 meters of the coordinates
4. Wait for the next update cycle (5 minutes)

### Entity Not Found Error

Make sure the latitude and longitude entity IDs you provided actually exist in your Home Assistant instance. You can check this in **Developer Tools** → **States**.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Attribution

This integration uses data from [OpenStreetMap](https://www.openstreetmap.org/copyright), which is made available under the Open Database License (ODbL).

## License

This project is licensed under the MIT License - see the LICENSE file for details.
