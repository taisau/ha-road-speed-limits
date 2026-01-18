"""Config flow for Road Speed Limits integration."""
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    CONF_DATA_SOURCE,
    CONF_LATITUDE_ENTITY,
    CONF_LONGITUDE_ENTITY,
    CONF_UNIT,
    DATA_SOURCE_HERE,
    DATA_SOURCE_NAMES,
    DATA_SOURCE_OSM,
    DATA_SOURCE_TOMTOM,
    DEFAULT_DATA_SOURCE,
    DEFAULT_UNIT,
    DOMAIN,
    HERE_API_KEY_NAME,
    TOMTOM_API_KEY_NAME,
    UNIT_KMH,
    UNIT_MPH,
    UNIT_NAMES,
)
from .helpers import get_coordinate_from_entity, validate_coordinates

_LOGGER = logging.getLogger(__name__)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    lat_entity = data[CONF_LATITUDE_ENTITY]
    lon_entity = data[CONF_LONGITUDE_ENTITY]

    # Check if entities exist
    lat_state = hass.states.get(lat_entity)
    lon_state = hass.states.get(lon_entity)

    if lat_state is None:
        raise ValueError(f"Latitude entity '{lat_entity}' not found")

    if lon_state is None:
        raise ValueError(f"Longitude entity '{lon_entity}' not found")

    # Extract and validate coordinates
    latitude = get_coordinate_from_entity(lat_state, "latitude")
    longitude = get_coordinate_from_entity(lon_state, "longitude")

    if not validate_coordinates(latitude, longitude):
        raise ValueError(
            f"Could not extract valid coordinates from entities. "
            f"Ensure entities have latitude/longitude attributes or numeric state values. "
            f"Got lat={latitude}, lon={longitude}"
        )

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
                vol.Required(
                    CONF_DATA_SOURCE, default=DEFAULT_DATA_SOURCE
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=DATA_SOURCE_OSM,
                                label=DATA_SOURCE_NAMES[DATA_SOURCE_OSM],
                            ),
                            selector.SelectOptionDict(
                                value=DATA_SOURCE_TOMTOM,
                                label=DATA_SOURCE_NAMES[DATA_SOURCE_TOMTOM],
                            ),
                            selector.SelectOptionDict(
                                value=DATA_SOURCE_HERE,
                                label=DATA_SOURCE_NAMES[DATA_SOURCE_HERE],
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_UNIT, default=DEFAULT_UNIT): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=UNIT_KMH,
                                label=UNIT_NAMES[UNIT_KMH],
                            ),
                            selector.SelectOptionDict(
                                value=UNIT_MPH,
                                label=UNIT_NAMES[UNIT_MPH],
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
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
        return RoadSpeedLimitsOptionsFlow()


class RoadSpeedLimitsOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Road Speed Limits."""

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

        # Pre-fill with current values (check both options and data)
        from .helpers import get_config_value

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_LATITUDE_ENTITY,
                    default=get_config_value(self.config_entry, CONF_LATITUDE_ENTITY),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "device_tracker", "person", "zone"]
                    )
                ),
                vol.Required(
                    CONF_LONGITUDE_ENTITY,
                    default=get_config_value(self.config_entry, CONF_LONGITUDE_ENTITY),
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "device_tracker", "person", "zone"]
                    )
                ),
                vol.Required(
                    CONF_DATA_SOURCE,
                    default=get_config_value(
                        self.config_entry, CONF_DATA_SOURCE, DEFAULT_DATA_SOURCE
                    ),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=DATA_SOURCE_OSM,
                                label=DATA_SOURCE_NAMES[DATA_SOURCE_OSM],
                            ),
                            selector.SelectOptionDict(
                                value=DATA_SOURCE_TOMTOM,
                                label=DATA_SOURCE_NAMES[DATA_SOURCE_TOMTOM],
                            ),
                            selector.SelectOptionDict(
                                value=DATA_SOURCE_HERE,
                                label=DATA_SOURCE_NAMES[DATA_SOURCE_HERE],
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_UNIT,
                    default=get_config_value(
                        self.config_entry, CONF_UNIT, DEFAULT_UNIT
                    ),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(
                                value=UNIT_KMH,
                                label=UNIT_NAMES[UNIT_KMH],
                            ),
                            selector.SelectOptionDict(
                                value=UNIT_MPH,
                                label=UNIT_NAMES[UNIT_MPH],
                            ),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            errors=errors,
        )
