"""Config flow for TwinFresh Atmo Mini integration."""
from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
from .const import DOMAIN, CONF_DEVICE_ID, CONF_NAME, DEFAULT_PORT, DEFAULT_PASSWORD, DEFAULT_NAME
from .atmo_fan import AtmoFan


class AtmoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TwinFresh Atmo Mini."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial setup step."""
        errors = {}
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
