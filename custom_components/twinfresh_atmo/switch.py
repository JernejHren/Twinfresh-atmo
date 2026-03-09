"""Switch entities for VENTS TwinFresh Atmo Mini."""
from __future__ import annotations
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN
from .coordinator import AtmoCoordinator

# (prop, display_suffix, param_id, entity_category)
SWITCH_TYPES = [
    ("humidity_sensor_state", "Humidity Sensor", 0x000f, EntityCategory.CONFIG),
    ("relay_sensor_state",    "Relay Sensor",    0x0014, EntityCategory.CONFIG),
    ("analogV_sensor_state",  "Analog V Sensor", 0x0016, EntityCategory.CONFIG),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: AtmoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        AtmoSwitch(coordinator, prop, suffix, param_id, cat)
        for prop, suffix, param_id, cat in SWITCH_TYPES
    ])


class AtmoSwitch(CoordinatorEntity, SwitchEntity):
    """Switch that enables or disables a device sensor input."""

    def __init__(self, coordinator, prop, suffix, param_id, entity_category):
        super().__init__(coordinator)
        self._fan = coordinator.fan
        self._prop = prop
        self._param_id = param_id
        slug = coordinator.slug
        name = coordinator.device_name

        self._attr_unique_id = f"{self._fan.id}_{prop}"
        self._attr_name = f"{name} {suffix}"
        self.entity_id = f"switch.{slug}_{prop}"
        self._attr_entity_category = entity_category
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name=name,
        )

    @property
    def is_on(self) -> bool | None:
        val = getattr(self._fan, self._prop, None)
        if val is None:
            return None
        return str(val).lower() in ("on", "1", "true")

    async def async_turn_on(self, **kwargs):
        await self.hass.async_add_executor_job(self._fan.write_param, self._param_id, 1)
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(self._fan.write_param, self._param_id, 0)
        await self.coordinator.async_refresh()
