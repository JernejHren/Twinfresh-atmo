"""Select entities for VENTS TwinFresh Atmo Mini."""
from __future__ import annotations
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN
from .coordinator import AtmoCoordinator

SPEED_OPTIONS   = ["low", "medium", "high"]
AIRFLOW_OPTIONS = ["ventilation", "heat_recovery", "air_supply"]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: AtmoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        AtmoSpeedSelect(coordinator),
        AtmoAirflowSelect(coordinator),
    ])


class AtmoSpeedSelect(CoordinatorEntity, SelectEntity):
    """Select entity to set fan speed (low / medium / high)."""

    _attr_icon = "mdi:speedometer"

    def __init__(self, coordinator: AtmoCoordinator) -> None:
        super().__init__(coordinator)
        self._fan = coordinator.fan
        slug = coordinator.slug
        name = coordinator.device_name

        self._attr_unique_id = f"{self._fan.id}_speed_select"
        self._attr_name = f"{name} Speed"
        self.entity_id = f"select.{slug}_speed"
        self._attr_options = SPEED_OPTIONS
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name=name,
        )

    @property
    def current_option(self) -> str | None:
        return self._fan.speed

    async def async_select_option(self, option: str) -> None:
        await self.hass.async_add_executor_job(self._fan.set_speed, option)
        await self.coordinator.async_refresh()


class AtmoAirflowSelect(CoordinatorEntity, SelectEntity):
    """Select entity to set airflow mode (ventilation / heat_recovery / air_supply)."""

    _attr_icon = "mdi:air-filter"

    def __init__(self, coordinator: AtmoCoordinator) -> None:
        super().__init__(coordinator)
        self._fan = coordinator.fan
        slug = coordinator.slug
        name = coordinator.device_name

        self._attr_unique_id = f"{self._fan.id}_airflow_select"
        self._attr_name = f"{name} Airflow"
        self.entity_id = f"select.{slug}_airflow"
        self._attr_options = AIRFLOW_OPTIONS
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name=name,
        )

    @property
    def current_option(self) -> str | None:
        return self._fan.airflow

    async def async_select_option(self, option: str) -> None:
        await self.hass.async_add_executor_job(self._fan.set_airflow, option)
        await self.coordinator.async_refresh()
