"""Sensor entities for VENTS TwinFresh Atmo Mini."""
from __future__ import annotations
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN
from .coordinator import AtmoCoordinator

# (prop, display_suffix, unit, device_class, state_class, entity_category, icon)
SENSOR_TYPES = [
    ("humidity",               "Humidity",           PERCENTAGE, SensorDeviceClass.HUMIDITY,  SensorStateClass.MEASUREMENT, None,                      "mdi:water-percent"),
    ("fan1_speed",             "Fan 1 RPM",          "RPM",      None,                        SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC, "mdi:fan"),
    ("fan2_speed",             "Fan 2 RPM",          "RPM",      None,                        SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC, "mdi:fan"),
    ("machine_hours",          "Operating Hours",    "h",        SensorDeviceClass.DURATION,  SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC, "mdi:clock-outline"),
    ("filter_timer_countdown", "Filter Time Left",   None,       None,                        None,                         EntityCategory.DIAGNOSTIC, "mdi:timer-sand"),
    ("firmware",               "Firmware",           None,       None,                        None,                         EntityCategory.DIAGNOSTIC, "mdi:chip"),
    ("curent_wifi_ip",         "WiFi IP",            None,       None,                        None,                         EntityCategory.DIAGNOSTIC, "mdi:ip-network"),
    ("alarm_status",           "Alarm",              None,       None,                        None,                         None,                      "mdi:alarm-light"),
    ("boost_time",             "Boost Duration",     "min",      None,                        None,                         EntityCategory.DIAGNOSTIC, "mdi:timer"),
    ("humidity_treshold",      "Humidity Threshold", PERCENTAGE, None,                        None,                         EntityCategory.CONFIG,     "mdi:water-percent"),
]


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: AtmoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        AtmoSensor(coordinator, prop, suffix, unit, dc, sc, cat, icon)
        for prop, suffix, unit, dc, sc, cat, icon in SENSOR_TYPES
    ])


class AtmoSensor(CoordinatorEntity, SensorEntity):
    """Generic sensor entity for a single AtmoFan property."""

    def __init__(self, coordinator, prop, suffix, unit, device_class, state_class, entity_category, icon):
        super().__init__(coordinator)
        self._fan = coordinator.fan
        self._prop = prop
        slug = coordinator.slug
        name = coordinator.device_name

        self._attr_unique_id = f"{self._fan.id}_{prop}"
        self._attr_name = f"{name} {suffix}"
        self.entity_id = f"sensor.{slug}_{prop}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_entity_category = entity_category
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name=name,
        )

    @property
    def native_value(self):
        return getattr(self._fan, self._prop, None)
