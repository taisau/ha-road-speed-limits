"""Binary sensor platform for Road Speed Limits integration."""
from homeassistant.components.binary_sensor import BinarySensorEntity
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
    """Set up the Road Speed Limits binary sensor."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    async_add_entities([RoadSpeedLimitsPollingSensor(coordinator, entry)])


class RoadSpeedLimitsPollingSensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of the polling state binary sensor."""

    def __init__(
        self,
        coordinator: RoadSpeedLimitsCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_name = "Polling Active"
        self._attr_unique_id = f"{entry.entry_id}_polling_active"
        self._attr_icon = "mdi:access-point-network"

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self.coordinator.polling_active
