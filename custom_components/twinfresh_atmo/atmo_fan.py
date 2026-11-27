"""Communication library for VENTS TwinFresh Atmo Mini Wi-Fi ventilation unit."""
from __future__ import annotations

import logging
import math
import socket
import threading
import time

_LOGGER = logging.getLogger(__name__)

HEADER_BYTES = b"\xfd\xfd"
PACKET_TYPE = 0x02

FUNC_READ = 0x01
FUNC_WRITE_RETURN = 0x03
FUNC_RESPONSE = 0x06

# Parameter ID to name mapping (based on pyEcoventV2 protocol)
PARAMS = {
    0x0001: "state",
    0x0002: "speed",
    0x0006: "boost_status",
    0x0007: "timer_mode",
    0x000B: "timer_counter",
    0x000F: "humidity_sensor_state",
    0x0014: "relay_sensor_state",
    0x0016: "analogV_sensor_state",
    0x0019: "humidity_treshold",
    0x0024: "battery_voltage",
    0x0025: "humidity",
    0x002D: "analogV",
    0x0032: "relay_status",
    0x0044: "man_speed",
    0x004A: "fan1_speed",
    0x004B: "fan2_speed",
    0x0064: "filter_timer_countdown",
    0x0065: "filter_timer_reset",  # write-only
    0x0066: "boost_time",
    0x006F: "rtc_time",
    0x0070: "rtc_date",
    0x007C: "device_search",
    0x007E: "machine_hours",
    0x0080: "reset_alarms",  # write-only
    0x0083: "alarm_status",
    0x0085: "cloud_server_state",
    0x0086: "firmware",
    0x0088: "filter_replacement_status",
    0x00A3: "curent_wifi_ip",
    0x00B7: "airflow",
    0x00B8: "analogV_treshold",
    0x00B9: "unit_type",
}

# Live telemetry polled every update_interval (default 30s)
FAST_PARAMS = [
    0x0001,  # state
    0x0002,  # speed
    0x00B7,  # airflow
    0x0044,  # man_speed
    0x0025,  # humidity
    0x004A,  # fan1_speed
    0x0006,  # boost_status
    0x0032,  # relay_status
    0x0083,  # alarm_status
    0x0085,  # cloud_server_state
]

# Slow-changing config/counters polled at startup, every 5 minutes, and after config/reset writes
SLOW_PARAMS = [
    0x000F,  # humidity_sensor_state
    0x0014,  # relay_sensor_state
    0x0016,  # analogV_sensor_state
    0x0019,  # humidity_treshold
    0x004B,  # fan2_speed
    0x0064,  # filter_timer_countdown
    0x0066,  # boost_time
    0x007E,  # machine_hours
    0x0088,  # filter_replacement_status
    0x00B8,  # analogV_treshold
]

# Static / slow-changing diagnostic metadata polled at startup and every 30 minutes
STATIC_PARAMS = [
    0x0086,  # firmware
    0x00A3,  # curent_wifi_ip
    0x00B9,  # unit_type
]

DYNAMIC_PARAMS = FAST_PARAMS + SLOW_PARAMS
SUPPORTED_PARAMS = FAST_PARAMS + SLOW_PARAMS + STATIC_PARAMS
SLOW_REFRESH_SECONDS = 300.0
STATIC_REFRESH_SECONDS = 1800.0

STATES = {0: "off", 1: "on", 2: "toggle"}
SPEEDS = {0: "standby", 1: "low", 2: "medium", 3: "high", 0xFF: "manual"}
AIRFLOWS = {0: "ventilation", 1: "heat_recovery", 2: "air_supply"}
STATUSES = {0: "off", 1: "on"}
ALARMS = {0: "no alarm", 1: "alarm", 2: "warning"}
TIMER_MODES = {0: "off", 1: "night", 2: "party"}


def chksum_bytes(payload: bytes) -> bytes:
    """Calculate 16-bit little-endian checksum over payload bytes."""
    return (sum(payload) & 0xFFFF).to_bytes(2, "little")


def build_header_bytes(device_id: str, password: str) -> bytes:
    """Build packet header: type + id_len + id_bytes + pwd_len + pwd_bytes."""
    id_bytes = device_id.encode("ascii")
    pwd_bytes = password.encode("ascii")
    return (
        bytes([PACKET_TYPE, len(id_bytes)])
        + id_bytes
        + bytes([len(pwd_bytes)])
        + pwd_bytes
    )


def build_packet(device_id: str, password: str, func: int | str, param_bytes: bytes | str) -> bytes:
    """Assemble full UDP packet with FDFD header, payload, and 16-bit checksum."""
    func_byte = int(func, 16) if isinstance(func, str) else func
    p_bytes = bytes.fromhex(param_bytes) if isinstance(param_bytes, str) else param_bytes
    body = build_header_bytes(device_id, password) + bytes([func_byte]) + p_bytes
    return HEADER_BYTES + body + chksum_bytes(body)


def parse_response(data: bytes) -> dict[int, str]:
    """Validate and parse UDP response packet. Returns {param_id: value_hex}."""
    results: dict[int, str] = {}
    if len(data) < 10 or data[:2] != HEADER_BYTES or data[2] != PACKET_TYPE:
        return results

    expected_crc = chksum_bytes(data[2:-2])
    if data[-2:] != expected_crc:
        _LOGGER.debug("Discarding packet with invalid checksum: got %s expected %s", data[-2:].hex(), expected_crc.hex())
        return results

    try:
        id_len = data[3]
        pointer = 4 + id_len
        if pointer >= len(data) - 2:
            return results
        pwd_len = data[pointer]
        pointer += 1 + pwd_len
        if pointer >= len(data) - 2:
            return results

        resp_func = data[pointer]
        if resp_func != FUNC_RESPONSE:
            _LOGGER.debug("Unexpected response function 0x%02X", resp_func)
        pointer += 1

        payload = data[pointer:-2]
        response = bytearray()
        ext_function = 0
        value_counter = 1
        high_byte = 0
        parameter = 1

        for p in payload:
            if parameter and p == 0xFF:
                ext_function = 0xFF
            elif parameter and p == 0xFE:
                ext_function = 0xFE
            elif parameter and p == 0xFD:
                ext_function = 0xFD
            else:
                if ext_function == 0xFF:
                    high_byte = p
                    ext_function = 1
                elif ext_function == 0xFE:
                    value_counter = p
                    ext_function = 2
                elif ext_function == 0xFD:
                    ext_function = 0
                else:
                    if parameter == 1:
                        response.append(high_byte)
                        parameter = 0
                    else:
                        value_counter -= 1
                    response.append(p)

            if value_counter <= 0:
                parameter = 1
                value_counter = 1
                high_byte = 0
                if len(response) >= 2:
                    pid = int.from_bytes(response[:2], "big")
                    val = response[2:].hex()
                    results[pid] = val
                response = bytearray()
    except Exception as exc:
        _LOGGER.debug("Error parsing response: %s", exc)
    return results


def decode(param_id: int, val_hex: str):
    """Decode hex value to a Python object based on parameter type."""
    if not val_hex:
        return None
    try:
        val_int = int(val_hex, 16)
        name = PARAMS.get(param_id, "")

        if name == "state":
            return STATES.get(val_int)
        if name == "speed":
            return SPEEDS.get(val_int)
        if name == "airflow":
            return AIRFLOWS.get(val_int)
        if name in (
            "boost_status",
            "relay_status",
            "heater_status",
            "filter_replacement_status",
            "relay_sensor_state",
        ):
            return STATUSES.get(val_int, "off")
        if name in ("humidity_sensor_state", "analogV_sensor_state", "cloud_server_state"):
            return STATES.get(val_int)
        if name == "alarm_status":
            return ALARMS.get(val_int)
        if name == "timer_mode":
            return TIMER_MODES.get(val_int)
        if name == "unit_type":
            types = {
                0x0300: "Vento Expert A50/85/100 V.2",
                0x0400: "Vento Expert Duo A30 V.2",
                0x0500: "Vento Expert A30 V.2",
                0x1100: "Vents Breezy 160-E",
                0x1A00: "TwinFresh Atmo Mini",
                0x1B00: "TwinFresh Atmo Mini",
            }
            return types.get(val_int, f"0x{val_int:04X}")
        if name == "humidity":
            return val_int
        if name in ("battery_voltage", "fan1_speed", "fan2_speed"):
            b = val_int.to_bytes(max(len(val_hex) // 2, 2), "big")
            return int.from_bytes(b[-2:], "little")
        if name == "man_speed":
            return val_int
        if name == "curent_wifi_ip":
            b = val_int.to_bytes(4, "big")
            return f"{b[0]}.{b[1]}.{b[2]}.{b[3]}"
        if name == "firmware":
            b = val_int.to_bytes(6, "big")
            return f"{b[0]}.{b[1]} ({int.from_bytes(b[4:6], 'little'):04d}-{b[3]:02d}-{b[2]:02d})"
        if name == "device_search":
            return bytes.fromhex(val_hex).decode("ascii", errors="replace")
        if name == "machine_hours":
            # 4-byte payload: [minutes, hours, days_lo, days_hi]
            b = val_int.to_bytes(max((len(val_hex) + 1) // 2, 4), "big")[-4:]
            minutes = b[0]
            hours = b[1]
            days = int.from_bytes(b[2:4], "little")
            return round(days * 24 + hours + minutes / 60, 1)
        if name == "filter_timer_countdown":
            b = val_int.to_bytes(max((len(val_hex) + 1) // 2, 4), "big")
            return f"{b[-2]}d {b[-3]:02d}h {b[-4]:02d}m"
        if name == "timer_counter":
            b = val_int.to_bytes(max(len(val_hex) // 2, 3), "big")
            return f"{b[-3]}h {b[-2]}m {b[-1]}s"
        return val_int
    except Exception as exc:
        _LOGGER.debug("Error decoding param 0x%04X: %s", param_id, exc)
        return None


class AtmoFan:
    """Thread-safe UDP client for the VENTS TwinFresh Atmo Mini ventilation unit."""

    def __init__(self, host: str, password: str, device_id: str, port: int = 4000) -> None:
        self._host = host
        self._password = password
        self._device_id = device_id
        self._port = port
        self._timeout = 1.5
        self._lock = threading.Lock()
        self._last_slow_poll = 0.0
        self._last_static_poll = 0.0
        self._force_slow_next = False
        self.data: dict = {}

    def _open_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self._timeout)
        return sock

    def _exchange(self, sock: socket.socket, pkt: bytes, retries: int = 1) -> bytes | None:
        """Send UDP packet via sendto/recvfrom with 1 quick retry on transient drop."""
        target = (self._host, self._port)
        for attempt in range(retries + 1):
            try:
                sock.sendto(pkt, target)
                resp, addr = sock.recvfrom(1024)
                if addr[0] == self._host:
                    return resp
            except socket.timeout:
                if attempt < retries:
                    time.sleep(0.08)
                    continue
                _LOGGER.debug("Timeout reading from %s", self._host)
                return None
            except OSError as exc:
                if attempt < retries:
                    time.sleep(0.1)
                    continue
                _LOGGER.debug("UDP error communicating with %s: %s", self._host, exc)
                return None
        return None

    def read_param(self, param_id: int, sock: socket.socket | None = None):
        """Read a single parameter from the device."""
        pkt = build_packet(self._device_id, self._password, FUNC_READ, param_id.to_bytes(2, "big"))
        if sock is not None:
            resp = self._exchange(sock, pkt, retries=1)
        else:
            with self._lock:
                with self._open_socket() as own_sock:
                    resp = self._exchange(own_sock, pkt, retries=1)

        if resp:
            results = parse_response(resp)
            for pid, val_hex in results.items():
                self.data[pid] = decode(pid, val_hex)
            return self.data.get(param_id)
        return None

    def write_param(self, param_id: int, value: int | str) -> bool:
        """Write a parameter to the device using pyEcoventV2 packet format."""
        param_hi = (param_id >> 8) & 0xFF
        param_lo = param_id & 0xFF
        if isinstance(value, int):
            val_bytes = value.to_bytes(max(1, (value.bit_length() + 7) // 8), "little")
        else:
            val_bytes = bytes.fromhex(str(value))

        out = bytearray()
        if param_hi != 0x00:
            out.extend((0xFF, param_hi))
        if len(val_bytes) > 1:
            out.extend((0xFE, len(val_bytes), param_lo))
        else:
            out.append(param_lo)
        out.extend(val_bytes)

        pkt = build_packet(self._device_id, self._password, FUNC_WRITE_RETURN, bytes(out))
        with self._lock:
            with self._open_socket() as sock:
                resp = self._exchange(sock, pkt, retries=2)
        if resp:
            for pid, val_hex in parse_response(resp).items():
                self.data[pid] = decode(pid, val_hex)
            if param_id in SLOW_PARAMS or param_id in (0x0065, 0x0080):
                self._force_slow_next = True
            return True
        return False

    def update(self) -> bool:
        """Poll fast telemetry every cycle, slow config/counters every 5m, static info every 30m."""
        now = time.monotonic()
        include_slow = (
            self._force_slow_next
            or not self._last_slow_poll
            or (now - self._last_slow_poll) >= SLOW_REFRESH_SECONDS
            or 0x007E not in self.data
        )
        include_static = (
            not self._last_static_poll
            or (now - self._last_static_poll) >= STATIC_REFRESH_SECONDS
            or 0x0086 not in self.data
        )
        params = list(FAST_PARAMS)
        if include_slow:
            params.extend(SLOW_PARAMS)
        if include_static:
            params.extend(STATIC_PARAMS)

        success = 0
        consecutive_failures = 0

        with self._lock:
            with self._open_socket() as sock:
                for idx, param_id in enumerate(params):
                    if idx > 0:
                        time.sleep(0.06)
                    pkt = build_packet(
                        self._device_id,
                        self._password,
                        FUNC_READ,
                        param_id.to_bytes(2, "big"),
                    )
                    retries = 1 if consecutive_failures == 0 else 0
                    resp = self._exchange(sock, pkt, retries=retries)
                    if resp:
                        parsed = parse_response(resp)
                        if parsed:
                            for pid, val_hex in parsed.items():
                                self.data[pid] = decode(pid, val_hex)
                            success += 1
                            consecutive_failures = 0
                            continue
                    consecutive_failures += 1
                    if consecutive_failures >= 4 and success == 0:
                        _LOGGER.debug(
                            "Aborting TwinFresh poll early after %d consecutive timeouts (%s)",
                            consecutive_failures,
                            self._host,
                        )
                        break

        if include_slow and success > 0:
            self._last_slow_poll = now
            self._force_slow_next = False
        if include_static and success > 0:
            self._last_static_poll = now

        _LOGGER.debug("Updated %d/%d parameters from %s", success, len(params), self._host)
        return success > 0

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def state(self) -> str | None:
        return self.data.get(0x0001)

    @property
    def speed(self) -> str | None:
        return self.data.get(0x0002)

    @property
    def airflow(self) -> str | None:
        return self.data.get(0x00B7)

    @property
    def humidity(self) -> int | None:
        return self.data.get(0x0025)

    @property
    def fan1_speed(self) -> int | None:
        return self.data.get(0x004A)

    @property
    def fan2_speed(self) -> int | None:
        return self.data.get(0x004B)

    @property
    def man_speed(self) -> int | None:
        return self.data.get(0x0044)

    @property
    def man_speed_pct(self) -> int | None:
        raw = self.man_speed
        if raw is None:
            return None
        return max(1, min(100, round(raw * 100 / 255)))

    @property
    def boost_status(self) -> str | None:
        return self.data.get(0x0006)

    @property
    def boost_time(self) -> int | None:
        return self.data.get(0x0066)

    @property
    def humidity_treshold(self) -> int | None:
        return self.data.get(0x0019)

    @property
    def analogV_treshold(self) -> int | None:
        return self.data.get(0x00B8)

    @property
    def humidity_sensor_state(self) -> str | None:
        return self.data.get(0x000F)

    @property
    def relay_sensor_state(self) -> str | None:
        return self.data.get(0x0014)

    @property
    def relay_status(self) -> str | None:
        return self.data.get(0x0032)

    @property
    def analogV_sensor_state(self) -> str | None:
        return self.data.get(0x0016)

    @property
    def filter_replacement_status(self) -> str | None:
        return self.data.get(0x0088)

    @property
    def alarm_status(self) -> str | None:
        return self.data.get(0x0083)

    @property
    def cloud_server_state(self) -> str | None:
        return self.data.get(0x0085)

    @property
    def machine_hours(self) -> float | None:
        return self.data.get(0x007E)

    @property
    def filter_timer_countdown(self) -> str | None:
        return self.data.get(0x0064)

    @property
    def firmware(self) -> str | None:
        return self.data.get(0x0086)

    @property
    def curent_wifi_ip(self) -> str | None:
        return self.data.get(0x00A3)

    @property
    def unit_type(self) -> str | None:
        return self.data.get(0x00B9)

    @property
    def id(self) -> str:
        return self._device_id

    @property
    def name(self) -> str:
        return "TwinFresh Atmo Mini"

    # ── Commands ──────────────────────────────────────────────────────────────

    def turn_on(self) -> bool:
        return self.write_param(0x0001, 1)

    def turn_off(self) -> bool:
        return self.write_param(0x0001, 0)

    def set_speed(self, speed: str) -> bool:
        """Set fan speed: standby=0, low=1, medium=2, high=3, manual=0xff."""
        mapping = {"standby": 0, "low": 1, "medium": 2, "high": 3, "manual": 0xFF}
        val = mapping.get(speed)
        if val is None:
            return False
        return self.write_param(0x0002, val)

    def set_man_speed(self, percent: int) -> bool:
        """Set manual speed as percentage (1-100%) and switch device to manual mode."""
        val = max(1, min(255, math.ceil(255 / 100 * max(1, min(100, percent)))))
        ok = self.write_param(0x0044, val)
        if ok and self.speed != "manual":
            self.write_param(0x0002, 0xFF)
        return ok

    def set_airflow(self, mode: str) -> bool:
        """Set airflow mode: ventilation=0, heat_recovery=1, air_supply=2."""
        mapping = {"ventilation": 0, "heat_recovery": 1, "air_supply": 2}
        val = mapping.get(mode)
        if val is None:
            return False
        return self.write_param(0x00B7, val)

    def reset_filter_timer(self) -> bool:
        """Reset the filter replacement timer."""
        return self.write_param(0x0065, 0)

    def reset_alarms(self) -> bool:
        """Clear all active alarms."""
        return self.write_param(0x0080, 0)
