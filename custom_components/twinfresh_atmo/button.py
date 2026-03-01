"""Button entities for VENTS TwinFresh Atmo Mini."""
from __future__ import annotations
from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN
from .coordinator import AtmoCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: AtmoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        AtmoResetFilterButton(coordinator),
        AtmoResetAlarmsButton(coordinator),
    ])


class AtmoResetFilterButton(CoordinatorEntity, ButtonEntity):
    """Button to reset the filter replacement timer."""

    _attr_icon = "mdi:air-filter"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AtmoCoordinator) -> None:
        super().__init__(coordinator)
        self._fan = coordinator.fan
        self._attr_unique_id = f"{self._fan.id}_reset_filter"
        self._attr_name = "Atmo Reset Filter Timer"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name="TwinFresh Atmo Mini",
        )

    async def async_press(self) -> None:
        """Reset the filter timer and refresh device state."""
        await self.hass.async_add_executor_job(self._fan.reset_filter_timer)
        await self.coordinator.async_refresh()


class AtmoResetAlarmsButton(CoordinatorEntity, ButtonEntity):
    """Button to clear all active alarms."""

    _attr_icon = "mdi:alarm-off"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: AtmoCoordinator) -> None:
        super().__init__(coordinator)
        self._fan = coordinator.fan
        self._attr_unique_id = f"{self._fan.id}_reset_alarms"
        self._attr_name = "Atmo Reset Alarms"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name="TwinFresh Atmo Mini",
        )

    async def async_press(self) -> None:
        """Clear all alarms and refresh device state."""
        await self.hass.async_add_executor_job(self._fan.reset_alarms)
        await self.coordinator.async_refresh()
