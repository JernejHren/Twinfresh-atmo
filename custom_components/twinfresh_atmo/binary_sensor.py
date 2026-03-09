"""Binary sensor entities for VENTS TwinFresh Atmo Mini."""
from __future__ import annotations
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN
from .coordinator import AtmoCoordinator

# (prop, display_suffix, device_class, entity_category, icon)
BINARY_SENSOR_TYPES = [
    ("filter_replacement_status", "Filter Replacement", BinarySensorDeviceClass.PROBLEM,      None,                      "mdi:air-filter"),
    ("alarm_status",              "Alarm",              BinarySensorDeviceClass.PROBLEM,      None,                      "mdi:alarm-light"),
    ("boost_status",              "Boost",              None,                                 None,                      "mdi:rocket-launch"),
    ("relay_status",              "Relay Status",       None,                                 EntityCategory.DIAGNOSTIC, "mdi:electric-switch"),
    ("cloud_server_state",        "Cloud Connection",   BinarySensorDeviceClass.CONNECTIVITY, None,                      "mdi:cloud"),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: AtmoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        AtmoBinarySensor(coordinator, prop, suffix, dc, cat, icon)
        for prop, suffix, dc, cat, icon in BINARY_SENSOR_TYPES
    ])


class AtmoBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that reads a single on/off property from AtmoFan."""

    def __init__(self, coordinator, prop, suffix, device_class, entity_category, icon):
        super().__init__(coordinator)
        self._fan = coordinator.fan
        self._prop = prop
        slug = coordinator.slug
        name = coordinator.device_name

        self._attr_unique_id = f"{self._fan.id}_{prop}"
        self._attr_name = f"{name} {suffix}"
        self.entity_id = f"binary_sensor.{slug}_{prop}"
        self._attr_device_class = device_class
        self._attr_entity_category = entity_category
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name=name,
        )

    @property
    def is_on(self) -> bool | None:
        val = getattr(self._fan, self._prop, None)
        if val is None:
            return None
        if isinstance(val, bool):
            return val
        if isinstance(val, int):
            return val != 0
        return str(val).lower() in ("on", "1", "true", "alarm", "warning")
