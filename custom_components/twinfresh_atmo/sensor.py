"""Sensor entities for VENTS TwinFresh Atmo Mini."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN
from .coordinator import AtmoCoordinator

# (prop, display_suffix, unit, device_class, state_class, entity_category, icon, options)
SENSOR_TYPES = [
    ("humidity", "Humidity", PERCENTAGE, SensorDeviceClass.HUMIDITY, SensorStateClass.MEASUREMENT, None, "mdi:water-percent", None),
    ("fan1_speed", "Fan 1 RPM", "RPM", None, SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC, "mdi:fan", None),
    ("fan2_speed", "Fan 2 RPM", "RPM", None, SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC, "mdi:fan", None),
    ("machine_hours", "Operating Hours", "h", SensorDeviceClass.DURATION, SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC, "mdi:clock-outline", None),
    ("filter_timer_countdown", "Filter Time Left", None, None, None, EntityCategory.DIAGNOSTIC, "mdi:timer-sand", None),
    ("firmware", "Firmware", None, None, None, EntityCategory.DIAGNOSTIC, "mdi:chip", None),
    ("curent_wifi_ip", "WiFi IP", None, None, None, EntityCategory.DIAGNOSTIC, "mdi:ip-network", None),
    ("alarm_status", "Alarm", None, SensorDeviceClass.ENUM, None, None, "mdi:alarm-light", ["no alarm", "alarm", "warning"]),
    ("boost_time", "Boost Duration", "min", None, None, EntityCategory.DIAGNOSTIC, "mdi:timer", None),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: AtmoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        AtmoSensor(coordinator, prop, suffix, unit, dc, sc, cat, icon, opts)
        for prop, suffix, unit, dc, sc, cat, icon, opts in SENSOR_TYPES
    ])


class AtmoSensor(CoordinatorEntity, SensorEntity):
    """Generic sensor entity for a single AtmoFan property."""

    def __init__(self, coordinator, prop, suffix, unit, device_class, state_class, entity_category, icon, options):
        super().__init__(coordinator)
        self._fan = coordinator.fan
        self._prop = prop

        self._attr_unique_id = f"{self._fan.id}_{prop}"
        self._attr_name = f"{coordinator.device_name} {suffix}"
        self._attr_suggested_object_id = f"{coordinator.slug}_{slugify(prop)}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_entity_category = entity_category
        self._attr_icon = icon
        if options is not None:
            self._attr_options = options
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self):
        return getattr(self._fan, self._prop, None)
