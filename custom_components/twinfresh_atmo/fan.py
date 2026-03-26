"""Fan entity for VENTS TwinFresh Atmo Mini."""
from __future__ import annotations
from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from .const import DOMAIN
from .coordinator import AtmoCoordinator

PRESET_MODES = ["low", "medium", "high"]
PRESET_TO_PCT = {"low": 33, "medium": 66, "high": 100}
AIRFLOW_TO_DIRECTION = {
    "ventilation":   "forward",
    "air_supply":    "reverse",
    "heat_recovery": None,
}


def pct_to_preset(pct: int) -> str:
    if pct <= 33:
        return "low"
    elif pct <= 66:
        return "medium"
    else:
        return "high"


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: AtmoCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AtmoFanEntity(coordinator)])


class AtmoFanEntity(CoordinatorEntity, FanEntity):
    """Representation of the TwinFresh Atmo Mini as a HA fan entity."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.OSCILLATE
        | FanEntityFeature.DIRECTION
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_preset_modes = PRESET_MODES
    _attr_speed_count = 3

    def __init__(self, coordinator: AtmoCoordinator) -> None:
        super().__init__(coordinator)
        self._fan = coordinator.fan
        slug = coordinator.slug
        name = coordinator.device_name

        self._attr_unique_id = f"{self._fan.id}_fan"
        self._attr_name = name
        self.entity_id = f"fan.{slug}_twinfresh"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._fan.id)},
            name=name,
            model="TwinFresh Atmo Mini",
            sw_version=self._fan.firmware,
            manufacturer="VENTS",
        )

    @property
    def is_on(self) -> bool:
        return self._fan.state == "on"

    @property
    def preset_mode(self) -> str | None:
        return self._fan.speed

    @property
    def percentage(self) -> int | None:
        return PRESET_TO_PCT.get(self._fan.speed or "")

    @property
    def current_direction(self) -> str | None:
        return AIRFLOW_TO_DIRECTION.get(self._fan.airflow or "")

    @property
    def oscillating(self) -> bool:
        return self._fan.airflow == "heat_recovery"

    @property
    def extra_state_attributes(self):
        return {
            "airflow_mode":   self._fan.airflow,
            "fan1_speed_rpm": self._fan.fan1_speed,
            "fan2_speed_rpm": self._fan.fan2_speed,
            "boost_status":   self._fan.boost_status,
            "cloud_server":   self._fan.cloud_server_state,
            "ip_address":     self._fan.curent_wifi_ip,
            "firmware":       self._fan.firmware,
            "machine_hours":  self._fan.machine_hours,
            "filter_ok":      self._fan.filter_replacement_status != "on",
        }

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        # Backward compatibility: some callers still pass `speed` instead of
        # `preset_mode`/`percentage` when turning on a fan.
        speed = kwargs.get("speed")
        if preset_mode is None and isinstance(speed, str) and speed in PRESET_MODES:
            preset_mode = speed

        await self.hass.async_add_executor_job(self._fan.turn_on)
        if preset_mode and preset_mode in PRESET_MODES:
            await self.hass.async_add_executor_job(self._fan.set_speed, preset_mode)
        elif percentage is not None:
            await self.hass.async_add_executor_job(self._fan.set_speed, pct_to_preset(percentage))
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs):
        await self.hass.async_add_executor_job(self._fan.turn_off)
        await self.coordinator.async_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if preset_mode in PRESET_MODES:
            if not self.is_on:
                await self.hass.async_add_executor_job(self._fan.turn_on)
            await self.hass.async_add_executor_job(self._fan.set_speed, preset_mode)
            await self.coordinator.async_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        if not self.is_on:
            await self.hass.async_add_executor_job(self._fan.turn_on)
        await self.hass.async_add_executor_job(self._fan.set_speed, pct_to_preset(percentage))
        await self.coordinator.async_refresh()

    async def async_oscillate(self, oscillating: bool) -> None:
        mode = "heat_recovery" if oscillating else "ventilation"
        await self.hass.async_add_executor_job(self._fan.set_airflow, mode)
        await self.coordinator.async_refresh()

    async def async_set_direction(self, direction: str) -> None:
        mode = "ventilation" if direction == "forward" else "air_supply"
        await self.hass.async_add_executor_job(self._fan.set_airflow, mode)
        await self.coordinator.async_refresh()
