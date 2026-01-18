"""Config flow for Road Speed Limits integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    CONF_LATITUDE_ENTITY,
    CONF_LONGITUDE_ENTITY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    lat_entity = data[CONF_LATITUDE_ENTITY]
    lon_entity = data[CONF_LONGITUDE_ENTITY]

    # Check if entities exist
    if hass.states.get(lat_entity) is None:
        raise ValueError(f"Latitude entity '{lat_entity}' not found")

    if hass.states.get(lon_entity) is None:
        raise ValueError(f"Longitude entity '{lon_entity}' not found")

    # Return info to be stored in the config entry
    return {"title": "Road Speed Limits"}


class RoadSpeedLimitsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Road Speed Limits."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except ValueError as err:
                _LOGGER.error("Validation failed: %s", err)
                errors["base"] = "invalid_entity"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # Create unique ID based on entity IDs
                await self.async_set_unique_id(
                    f"{user_input[CONF_LATITUDE_ENTITY]}_{user_input[CONF_LONGITUDE_ENTITY]}"
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(title=info["title"], data=user_input)

        # Show the configuration form
        data_schema = vol.Schema(
            {
                vol.Required(CONF_LATITUDE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "device_tracker", "person", "zone"]
                    )
                ),
                vol.Required(CONF_LONGITUDE_ENTITY): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "device_tracker", "person", "zone"]
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return RoadSpeedLimitsOptionsFlow(config_entry)


class RoadSpeedLimitsOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Road Speed Limits."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await validate_input(self.hass, user_input)
            except ValueError as err:
                _LOGGER.error("Validation failed: %s", err)
                errors["base"] = "invalid_entity"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="", data=user_input)

        # Pre-fill with current values
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_LATITUDE_ENTITY,
                    default=self.config_entry.data.get(CONF_LATITUDE_ENTITY),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "device_tracker", "person", "zone"]
                    )
                ),
                vol.Required(
                    CONF_LONGITUDE_ENTITY,
                    default=self.config_entry.data.get(CONF_LONGITUDE_ENTITY),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "device_tracker", "person", "zone"]
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )
