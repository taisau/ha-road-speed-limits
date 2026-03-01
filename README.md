# GEMINI.md - ha-road-speed-limits

## Context
Home Assistant custom integration that displays current road speed limits based on GPS coordinates using multiple data sources (OpenStreetMap, TomTom, HERE Maps).

### Key Features
- **Multiple Data Sources**: Choice between OpenStreetMap (free), TomTom, or HERE Maps.
- **Automatic Fallback**: Automatically falls back to OpenStreetMap if the primary provider fails.
- **Flexible Location Input**: Supports single GPS sensors with attributes, device trackers, or separate lat/lon sensor entities.
- **Poll Rate**: Updates every 5 minutes.

### Technical Details & Usage
- **Entity**: `sensor.road_speed_limit`.
- **Attributes**: `road_name`, `data_source`, `active_provider`, `fallback_active`, `last_update`.
- **Setup**: Configured via UI. Requires API keys for TomTom/HERE.

### Release Procedure (Critical)
HACS requires formal GitHub releases to detect updates:
1. **Bump Version**: Update `version` in `custom_components/road_speed_limits/manifest.json`.
2. **Commit & Push**: Push changes to GitHub.
3. **Tag**: Create and push a git tag (e.g., `git tag v0.0.x`).
4. **Release**: Create a formal GitHub release (`gh release create v0.0.x`).

## Global Context
This project inherits global context from: /home/taisau/workspace/GEMINI.md

## Context7 Documentation
- Preferred User Docs: `/home-assistant/home-assistant.io`
- Preferred Dev Docs: `/websites/developers_home-assistant_io`
