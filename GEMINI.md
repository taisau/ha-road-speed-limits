# Project Context: ha-road-speed-limits

## Project Overview
**ha-road-speed-limits** is a Home Assistant HACS (Home Assistant Community Store) integration designed to aggregate and display free speed limit information from various open sources (e.g., OpenStreetMap).

## Key Information
- **Distribution:** Available via HACS.
- **Source Control:** Hosted on a GitHub repository named `ha-road-speed-limits`.

## Project Type
**Code Project** - Python-based Home Assistant Integration.

## Technology Stack
- **Platform:** Home Assistant
- **Language:** Python
- **Distribution:** HACS (Home Assistant Community Store)

## Expected Architecture
As a Home Assistant integration, the project should follow this standard directory structure:

```
ha-road-speed-limits/
├── custom_components/
│   └── ha_road_speed_limits/
│       ├── __init__.py
│       ├── manifest.json
│       ├── sensor.py (or other platform files)
│       └── services.yaml
├── hacs.json (HACS metadata)
└── README.md
```

## Building and Running
Since this is a Home Assistant integration, "running" it implies installing it into a Home Assistant instance.

1.  **Development:**
    - Code is typically placed in `custom_components/ha_road_speed_limits`.
2.  **Installation (Manual):**
    - Copy the `custom_components/ha_road_speed_limits` folder to the `config/custom_components/` directory of your Home Assistant instance.
    - Restart Home Assistant.
3.  **Testing:**
    - `pytest` is commonly used for testing HA integrations. (TODO: Set up testing environment).

## Development Conventions
- Follow [Home Assistant Developer Docs](https://developers.home-assistant.io/).
- Ensure `manifest.json` is accurate.
- Use asynchronous programming (`async`/`await`) as per HA standards.
