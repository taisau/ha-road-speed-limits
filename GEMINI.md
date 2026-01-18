# Project Context: ha-road-speed-limits

## Project Overview
**ha-road-speed-limits** is a Home Assistant HACS (Home Assistant Community Store) integration designed to aggregate and display free speed limit information from various open sources (e.g., OpenStreetMap).

## Key Information
- **Distribution:** Available via HACS.
- **Source Control:** Hosted on a GitHub repository named `ha-road-speed-limits`.

## Key Features
- **Multi-Source Support:** Users can select from available free sources for speed limit data, including:
    - OpenStreetMap (OSM)
    - HERE Maps
    - TomTom

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

## Release Procedure
Because this project is distributed via HACS, the following steps **MUST** be followed for every update:
1.  **Bump Version**: Increment the `version` in `custom_components/road_speed_limits/manifest.json`.
2.  **Commit**: Commit the changes (including the version bump).
3.  **Push**: Push the commit to GitHub.
4.  **Tag**: Create a git tag for the new version (e.g., `git tag v0.0.2`) and push it (`git push origin v0.0.2`). HACS requires this tag to detect the update.
