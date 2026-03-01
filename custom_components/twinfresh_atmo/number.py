"""Number entities for VENTS TwinFresh Atmo Mini."""
from __future__ import annotations
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN
from .coordinator import AtmoCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: AtmoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        AtmoNumber(coordinator, "humidity_treshold", "Humidity Threshold",    0x0019, 30, 90,  1, PERCENTAGE, EntityCategory.CONFIG),
        AtmoNumber(coordinator, "analogV_treshold",  "Analog Voltage Threshold", 0x00b8, 0, 100, 1, None,      EntityCategory.CONFIG),
        AtmoNumber(coordinator, "boost_time",        "Boost Duration",        0x0066, 1,  60,  1, "min",      EntityCategory.CONFIG),
    ])


class AtmoNumber(CoordinatorEntity, NumberEntity):
    """Adjustable numeric parameter with a slider."""

    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator, prop, name, param_id, min_val, max_val, step, unit, entity_category):
        super().__init__(coordinator)
        self._fan = coordinator.fan
        self._prop = prop
        self._param_id = param_id
        self._attr_name = f"Atmo {name}"
        self._attr_unique_id = f"{self._fan.id}_{prop}_number"
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_entity_category = entity_category
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name="TwinFresh Atmo Mini",
        )

    @property
    def native_value(self) -> float | None:
        val = getattr(self._fan, self._prop, None)
        if val is None:
            return None
        try:
            return float(val)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        await self.hass.async_add_executor_job(self._fan.write_param, self._param_id, int(value))
        await self.coordinator.async_refresh()
