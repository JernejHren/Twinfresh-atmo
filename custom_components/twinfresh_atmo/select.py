"""Select entities for VENTS TwinFresh Atmo Mini."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AtmoCoordinator

SPEED_OPTIONS = ["standby", "low", "medium", "high", "manual"]
AIRFLOW_OPTIONS = ["ventilation", "heat_recovery", "air_supply"]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: AtmoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        AtmoSpeedSelect(coordinator),
        AtmoAirflowSelect(coordinator),
    ])


class AtmoSpeedSelect(CoordinatorEntity, SelectEntity):
    """Select entity to set fan speed (standby / low / medium / high / manual)."""

    _attr_icon = "mdi:speedometer"
    _attr_options = SPEED_OPTIONS

    def __init__(self, coordinator: AtmoCoordinator) -> None:
        super().__init__(coordinator)
        self._fan = coordinator.fan
        self._attr_unique_id = f"{self._fan.id}_speed_select"
        self._attr_name = f"{coordinator.device_name} Speed"
        self._attr_suggested_object_id = f"{coordinator.slug}_speed"
        self._attr_device_info = coordinator.device_info

    @property
    def current_option(self) -> str | None:
        speed = self._fan.speed
        return speed if speed in SPEED_OPTIONS else None

    async def async_select_option(self, option: str) -> None:
        await self.hass.async_add_executor_job(self._fan.set_speed, option)
        await self.coordinator.async_refresh()


class AtmoAirflowSelect(CoordinatorEntity, SelectEntity):
    """Select entity to set airflow mode (ventilation / heat_recovery / air_supply)."""

    _attr_icon = "mdi:air-filter"
    _attr_options = AIRFLOW_OPTIONS

    def __init__(self, coordinator: AtmoCoordinator) -> None:
        super().__init__(coordinator)
        self._fan = coordinator.fan
        self._attr_unique_id = f"{self._fan.id}_airflow_select"
        self._attr_name = f"{coordinator.device_name} Airflow"
        self._attr_suggested_object_id = f"{coordinator.slug}_airflow"
        self._attr_device_info = coordinator.device_info

    @property
    def current_option(self) -> str | None:
        airflow = self._fan.airflow
        return airflow if airflow in AIRFLOW_OPTIONS else None

    async def async_select_option(self, option: str) -> None:
        await self.hass.async_add_executor_job(self._fan.set_airflow, option)
        await self.coordinator.async_refresh()
