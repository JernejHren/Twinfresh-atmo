"""Sensor entities for VENTS TwinFresh Atmo Mini."""
from __future__ import annotations
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN
from .coordinator import AtmoCoordinator


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: AtmoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        AtmoSensor(coordinator, "humidity",               "Humidity",            PERCENTAGE, SensorDeviceClass.HUMIDITY,  SensorStateClass.MEASUREMENT, None,                      "mdi:water-percent"),
        AtmoSensor(coordinator, "fan1_speed",             "Fan 1 RPM",           "RPM",      None,                        SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC, "mdi:fan"),
        AtmoSensor(coordinator, "fan2_speed",             "Fan 2 RPM",           "RPM",      None,                        SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC, "mdi:fan"),
        AtmoSensor(coordinator, "machine_hours",          "Operating Hours",     "h",        SensorDeviceClass.DURATION,  SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC, "mdi:clock-outline"),
        AtmoSensor(coordinator, "filter_timer_countdown", "Filter Time Left",    None,       None,                        None,                         EntityCategory.DIAGNOSTIC, "mdi:timer-sand"),
        AtmoSensor(coordinator, "firmware",               "Firmware",            None,       None,                        None,                         EntityCategory.DIAGNOSTIC, "mdi:chip"),
        AtmoSensor(coordinator, "curent_wifi_ip",         "WiFi IP",             None,       None,                        None,                         EntityCategory.DIAGNOSTIC, "mdi:ip-network"),
        AtmoSensor(coordinator, "alarm_status",           "Alarm",               None,       None,                        None,                         None,                      "mdi:alarm-light"),
        AtmoSensor(coordinator, "boost_time",             "Boost Duration",      "min",      None,                        None,                         EntityCategory.DIAGNOSTIC, "mdi:timer"),
        AtmoSensor(coordinator, "humidity_treshold",      "Humidity Threshold",  PERCENTAGE, None,                        None,                         EntityCategory.CONFIG,     "mdi:water-percent"),
    ])


class AtmoSensor(CoordinatorEntity, SensorEntity):
    """Generic sensor entity for a single AtmoFan property."""

    def __init__(self, coordinator, prop, name, unit, device_class, state_class, entity_category, icon=None):
        super().__init__(coordinator)
        self._fan = coordinator.fan
        self._prop = prop
        self._attr_name = f"Atmo {name}"
        self._attr_unique_id = f"{self._fan.id}_{prop}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_entity_category = entity_category
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name="TwinFresh Atmo Mini",
        )

    @property
    def native_value(self):
        return getattr(self._fan, self._prop, None)
