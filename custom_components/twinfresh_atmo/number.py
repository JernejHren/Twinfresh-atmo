"""Number entities for VENTS TwinFresh Atmo Mini."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN
from .coordinator import AtmoCoordinator

# (prop, display_suffix, param_id, min, max, step, unit, entity_category, icon)
NUMBER_TYPES = [
    ("humidity_treshold", "Humidity Threshold", 0x0019, 30, 90, 1, PERCENTAGE, EntityCategory.CONFIG, "mdi:water-percent"),
    ("analogV_treshold", "Analog Voltage Threshold", 0x00B8, 0, 100, 1, None, EntityCategory.CONFIG, "mdi:sine-wave"),
    ("boost_time", "Boost Duration", 0x0066, 1, 60, 1, "min", EntityCategory.CONFIG, "mdi:timer"),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: AtmoCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[NumberEntity] = [
        AtmoNumber(coordinator, prop, suffix, param_id, mn, mx, step, unit, cat, icon)
        for prop, suffix, param_id, mn, mx, step, unit, cat, icon in NUMBER_TYPES
    ]
    entities.append(AtmoManualSpeedNumber(coordinator))
    async_add_entities(entities)


class AtmoNumber(CoordinatorEntity, NumberEntity):
    """Adjustable numeric parameter with a slider."""

    _attr_mode = NumberMode.SLIDER

    def __init__(self, coordinator, prop, suffix, param_id, min_val, max_val, step, unit, entity_category, icon):
        super().__init__(coordinator)
        self._fan = coordinator.fan
        self._prop = prop
        self._param_id = param_id

        self._attr_unique_id = f"{self._fan.id}_{prop}_number"
        self._attr_name = f"{coordinator.device_name} {suffix}"
        self._attr_suggested_object_id = f"{coordinator.slug}_{slugify(prop)}"
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_entity_category = entity_category
        self._attr_icon = icon
        self._attr_device_info = coordinator.device_info

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


class AtmoManualSpeedNumber(CoordinatorEntity, NumberEntity):
    """Stepless manual fan speed slider (1-100%)."""

    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 1
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:fan-speed-1"

    def __init__(self, coordinator: AtmoCoordinator) -> None:
        super().__init__(coordinator)
        self._fan = coordinator.fan
        self._attr_unique_id = f"{self._fan.id}_man_speed_number"
        self._attr_name = f"{coordinator.device_name} Manual Speed"
        self._attr_suggested_object_id = f"{coordinator.slug}_manual_speed"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | None:
        pct = self._fan.man_speed_pct
        return float(pct) if pct is not None else None

    async def async_set_native_value(self, value: float) -> None:
        if not self._fan.state == "on":
            await self.hass.async_add_executor_job(self._fan.turn_on)
        await self.hass.async_add_executor_job(self._fan.set_man_speed, int(value))
        await self.coordinator.async_refresh()
