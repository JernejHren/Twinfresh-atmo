"""DataUpdateCoordinator for TwinFresh Atmo Mini."""
from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import slugify

from .atmo_fan import AtmoFan
from .const import (
    CONF_DEVICE_ID,
    CONF_NAME,
    CONF_UPDATE_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DOMAIN,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class AtmoCoordinator(DataUpdateCoordinator):
    """Coordinator that periodically fetches data from the ventilation unit."""

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        merged = {**config.data, **config.options}
        self.fan = AtmoFan(
            merged[CONF_HOST],
            merged[CONF_PASSWORD],
            config.data[CONF_DEVICE_ID],
            merged.get(CONF_PORT, DEFAULT_PORT),
        )
        self.device_name: str = config.data.get(CONF_NAME, DEFAULT_NAME)
        self.slug: str = slugify(self.device_name)
        self._consecutive_failures = 0
        interval = int(merged.get(CONF_UPDATE_INTERVAL, UPDATE_INTERVAL))

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
            config_entry=config,
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return shared DeviceInfo with firmware and model metadata."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.fan.id)},
            name=self.device_name,
            manufacturer="VENTS",
            model=self.fan.unit_type or "TwinFresh Atmo Mini",
            sw_version=self.fan.firmware,
        )

    async def _async_update_data(self):
        """Fetch supported parameters from the device."""
        ok = await self.hass.async_add_executor_job(self.fan.update)
        if not ok:
            self._consecutive_failures += 1
            # Tolerate 2 consecutive missed polls (~60s) when we already have cached state,
            # since the TwinFresh Wi-Fi MCU briefly pauses its UDP listener every few minutes.
            if self.fan.data and self._consecutive_failures < 3:
                _LOGGER.debug(
                    "Transient poll miss %d/3 for TwinFresh at %s:%s; keeping cached state",
                    self._consecutive_failures,
                    self.fan._host,
                    self.fan._port,
                )
                return self.fan.data
            raise UpdateFailed(
                f"TwinFresh unit at {self.fan._host}:{self.fan._port} did not respond "
                f"({self._consecutive_failures} consecutive polls)"
            )
        self._consecutive_failures = 0
        return self.fan.data
