"""DataUpdateCoordinator for TwinFresh Atmo Mini."""
from __future__ import annotations
from datetime import timedelta
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import slugify
from .atmo_fan import AtmoFan
from .const import DOMAIN, CONF_DEVICE_ID, CONF_NAME, DEFAULT_NAME, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class AtmoCoordinator(DataUpdateCoordinator):
    """Coordinator that periodically fetches data from the ventilation unit."""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        self.fan = AtmoFan(
            config.data[CONF_HOST],
            config.data[CONF_PASSWORD],
            config.data[CONF_DEVICE_ID],
            config.data[CONF_PORT],
        )
        # Human-readable name set by the user during config flow (e.g. "Bad EG")
        self.device_name: str = config.data.get(CONF_NAME, DEFAULT_NAME)

        # URL-safe slug used as entity ID prefix (e.g. "bad_eg")
        self.slug: str = slugify(self.device_name)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self):
        """Fetch all supported parameters from the device."""
        ok = await self.hass.async_add_executor_job(self.fan.update)
        if not ok:
            raise UpdateFailed("Device did not respond")
        return self.fan.data
