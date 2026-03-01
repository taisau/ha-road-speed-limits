"""Button platform for Road Speed Limits integration."""
from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RoadSpeedLimitsCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Road Speed Limits button."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    buttons = [RoadSpeedLimitsManualUpdateButton(coordinator, entry)]
    
    # Add provider-specific buttons if keys are configured
    from .const import DATA_SOURCE_HERE, DATA_SOURCE_TOMTOM, DATA_SOURCE_OSM
    
    if DATA_SOURCE_OSM in coordinator.providers:
        buttons.append(RoadSpeedLimitsProviderRefreshButton(coordinator, entry, DATA_SOURCE_OSM, "OSM"))
        
    if DATA_SOURCE_TOMTOM in coordinator.providers:
        buttons.append(RoadSpeedLimitsProviderRefreshButton(coordinator, entry, DATA_SOURCE_TOMTOM, "TomTom"))
        
    if DATA_SOURCE_HERE in coordinator.providers:
        buttons.append(RoadSpeedLimitsProviderRefreshButton(coordinator, entry, DATA_SOURCE_HERE, "HERE"))

    async_add_entities(buttons)


class RoadSpeedLimitsManualUpdateButton(CoordinatorEntity, ButtonEntity):
    """Representation of a button to manually trigger a speed limit update."""

    def __init__(
        self,
        coordinator: RoadSpeedLimitsCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._attr_name = "Road Speed Limit Manual Update"
        self._attr_unique_id = f"{entry.entry_id}_manual_update"
        self._attr_icon = "mdi:refresh"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_request_refresh()


class RoadSpeedLimitsProviderRefreshButton(CoordinatorEntity, ButtonEntity):
    """Representation of a button to refresh a specific provider."""

    def __init__(
        self,
        coordinator: RoadSpeedLimitsCoordinator,
        entry: ConfigEntry,
        provider_key: str,
        provider_name: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.provider_key = provider_key
        self._attr_name = f"Refresh {provider_name} Speed Limit"
        self._attr_unique_id = f"{entry.entry_id}_refresh_{provider_key}"
        self._attr_icon = "mdi:refresh-circle"
        self._attr_entity_registry_enabled_default = False  # Keep UI clean by default

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.coordinator.async_refresh_with_provider(self.provider_key)
