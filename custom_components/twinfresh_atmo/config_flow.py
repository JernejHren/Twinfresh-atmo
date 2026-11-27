"""Config and options flow for TwinFresh Atmo Mini integration."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
from homeassistant.core import callback

from .atmo_fan import AtmoFan
from .const import (
    CONF_DEVICE_ID,
    CONF_NAME,
    CONF_UPDATE_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DOMAIN,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    UPDATE_INTERVAL,
)


class AtmoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TwinFresh Atmo Mini."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> AtmoOptionsFlowHandler:
        """Return options flow handler to reconfigure host/port/password."""
        return AtmoOptionsFlowHandler()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial setup step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                fan = AtmoFan(
                    user_input[CONF_HOST],
                    user_input[CONF_PASSWORD],
                    user_input[CONF_DEVICE_ID],
                    user_input[CONF_PORT],
                )
                result = await self.hass.async_add_executor_job(fan.read_param, 0x0001)
                if result is None:
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data=user_input,
                    )
            except Exception:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
                vol.Required(CONF_DEVICE_ID): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
            }),
            errors=errors,
        )


class AtmoOptionsFlowHandler(config_entries.OptionsFlow):
    """Allow updating IP address, port, or password without recreating entities."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}
        merged = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            try:
                fan = AtmoFan(
                    user_input[CONF_HOST],
                    user_input[CONF_PASSWORD],
                    self.config_entry.data[CONF_DEVICE_ID],
                    user_input[CONF_PORT],
                )
                result = await self.hass.async_add_executor_job(fan.read_param, 0x0001)
                if result is None:
                    errors["base"] = "cannot_connect"
                else:
                    return self.async_create_entry(title="", data=user_input)
            except Exception:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST, default=merged.get(CONF_HOST, "")): str,
                vol.Required(CONF_PASSWORD, default=merged.get(CONF_PASSWORD, DEFAULT_PASSWORD)): str,
                vol.Optional(CONF_PORT, default=merged.get(CONF_PORT, DEFAULT_PORT)): int,
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=merged.get(CONF_UPDATE_INTERVAL, UPDATE_INTERVAL),
                ): vol.All(int, vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL)),
            }),
            errors=errors,
        )
