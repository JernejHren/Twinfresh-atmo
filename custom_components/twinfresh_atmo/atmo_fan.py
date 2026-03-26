"""Communication library for VENTS TwinFresh Atmo Mini Wi-Fi ventilation unit."""
import socket
import logging
import time
import math

_LOGGER = logging.getLogger(__name__)

HEADER = "FDFD"
TYPE   = "02"

# Parameter ID to name mapping (based on pyEcoventV2 protocol)
PARAMS = {
    0x0001: "state",
    0x0002: "speed",
    0x0006: "boost_status",
    0x0007: "timer_mode",
    0x000b: "timer_counter",
    0x000f: "humidity_sensor_state",
    0x0014: "relay_sensor_state",
    0x0016: "analogV_sensor_state",
    0x0019: "humidity_treshold",
    0x0024: "battery_voltage",
    0x0025: "humidity",
    0x002d: "analogV",
    0x0032: "relay_status",
    0x0044: "man_speed",
    0x004a: "fan1_speed",
    0x004b: "fan2_speed",
    0x0064: "filter_timer_countdown",
    0x0065: "filter_timer_reset",   # write-only
    0x0066: "boost_time",
    0x006f: "rtc_time",
    0x0070: "rtc_date",
    0x007c: "device_search",
    0x007e: "machine_hours",
    0x0080: "reset_alarms",         # write-only
    0x0083: "alarm_status",
    0x0085: "cloud_server_state",
    0x0086: "firmware",
    0x0088: "filter_replacement_status",
    0x00a3: "curent_wifi_ip",
    0x00b7: "airflow",
    0x00b8: "analogV_treshold",
    0x00b9: "unit_type",
}

# Parameters confirmed to return valid data on TwinFresh Atmo Mini
SUPPORTED_PARAMS = [
    0x0001, 0x0002, 0x0006, 0x0007, 0x000b,
    0x000f, 0x0014, 0x0016, 0x0019, 0x0024,
    0x0025, 0x002d, 0x0032, 0x0044, 0x004a,
    0x004b, 0x0064, 0x0066, 0x006f, 0x0070,
    0x007c, 0x007e, 0x0083, 0x0085, 0x0086,
    0x0088, 0x00a3, 0x00b7, 0x00b8, 0x00b9,
]

STATES      = {0: "off",  1: "on",  2: "toggle"}
SPEEDS      = {0: "standby", 1: "low", 2: "medium", 3: "high", 0xff: "manual"}
AIRFLOWS    = {0: "ventilation", 1: "heat_recovery", 2: "air_supply"}
STATUSES    = {0: "off",  1: "on"}
ALARMS      = {0: "no alarm", 1: "alarm", 2: "warning"}
TIMER_MODES = {0: "off",  1: "night", 2: "party"}

FUNC_READ         = "01"
FUNC_WRITE_RETURN = "03"


def str2hex(s: str) -> str:
    """Convert ASCII string to hex string."""
    return "".join("{:02x}".format(ord(c)) for c in s)


def hex2str(h: str) -> str:
    """Convert hex string to ASCII string."""
    try:
        return "".join(chr(int(h[i:i+2], 16)) for i in range(0, len(h), 2))
    except Exception:
        return h


def chksum(hex_msg: str) -> str:
    """Calculate checksum: sum of all bytes, little-endian 16-bit."""
    vals = [int(hex_msg[i:i+2], 16) for i in range(0, len(hex_msg), 2)]
    total = hex(sum(vals)).replace("0x", "").zfill(4)
    b = bytearray.fromhex(total)
    return hex(b[1]).replace("0x", "").zfill(2) + hex(b[0]).replace("0x", "").zfill(2)


def build_header(device_id: str, password: str) -> str:
    """Build packet header: type + id_size + id_hex + pwd_size + pwd_hex."""
    id_hex   = str2hex(device_id)
    pwd_hex  = str2hex(password)
    id_size  = hex(len(device_id)).replace("0x", "").zfill(2)
    pwd_size = hex(len(password)).replace("0x", "").zfill(2)
    return f"{TYPE}{id_size}{id_hex}{pwd_size}{pwd_hex}"


def build_packet(device_id: str, password: str, func: str, param_hex: str) -> bytes:
    """Assemble full UDP packet with header, payload and checksum."""
    header  = build_header(device_id, password)
    payload = header + func + param_hex
    full    = HEADER + payload + chksum(payload)
    return bytes.fromhex(full)


def parse_response(data: bytes) -> dict:
    """Parse UDP response packet. Returns {param_id: value_hex}."""
    results = {}
    if len(data) <= 22:
        return results
    try:
        pointer  = 20
        pwd_size = data[pointer]; pointer += 1
        pointer += pwd_size
        if pointer >= len(data):
            return results
        pointer += 1  # skip function byte

        length  = len(data) - 2
        payload = data[pointer:length]

        response      = bytearray()
        ext_function  = 0
        value_counter = 1
        high_byte     = 0
        parameter     = 1

        for p in payload:
            if parameter and p == 0xff:
                ext_function = 0xff
            elif parameter and p == 0xfe:
                ext_function = 0xfe
            elif parameter and p == 0xfd:
                ext_function = 0xfd
            else:
                if ext_function == 0xff:
                    high_byte = p; ext_function = 1
                elif ext_function == 0xfe:
                    value_counter = p; ext_function = 2
                elif ext_function == 0xfd:
                    pass
                else:
                    if parameter == 1:
                        response.append(high_byte); parameter = 0
                    else:
                        value_counter -= 1
                    response.append(p)

            if value_counter <= 0:
                parameter = 1; value_counter = 1; high_byte = 0
                if len(response) >= 2:
                    pid = int(response[:2].hex(), 16)
                    val = response[2:].hex()
                    results[pid] = val
                response = bytearray()
    except Exception as e:
        _LOGGER.warning("Error parsing response: %s", e)
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
        elif name == "speed":
            return SPEEDS.get(val_int)
        elif name == "airflow":
            return AIRFLOWS.get(val_int)
        elif name in ("boost_status", "relay_status", "heater_status",
                      "filter_replacement_status", "relay_sensor_state"):
            return STATUSES.get(val_int, "off")
        elif name in ("humidity_sensor_state", "analogV_sensor_state", "cloud_server_state"):
            return STATES.get(val_int)
        elif name == "alarm_status":
            return ALARMS.get(val_int)
        elif name == "timer_mode":
            return TIMER_MODES.get(val_int)
        elif name == "unit_type":
            types = {
                0x0300: "Vento Expert A50/85/100 V.2",
                0x0400: "Vento Expert Duo A30 V.2",
                0x0500: "Vento Expert A30 V.2",
                0x1100: "Vents Breezy 160-E",
                0x1a00: "TwinFresh Atmo Mini",
            }
            return types.get(val_int, f"0x{val_int:04X}")
        elif name == "humidity":
            return val_int
        elif name == "battery_voltage":
            # 2-byte little-endian value in mV
            b = int(val_hex, 16).to_bytes(max(len(val_hex) // 2, 2), "big")
            return int.from_bytes(b[-2:], "little")
        elif name == "man_speed":
            return val_int
        elif name in ("fan1_speed", "fan2_speed"):
            # 2-byte little-endian RPM value
            b = int(val_hex, 16).to_bytes(max(len(val_hex) // 2, 2), "big")
            return int.from_bytes(b[-2:], "little")
        elif name == "curent_wifi_ip":
            b = int(val_hex, 16).to_bytes(4, "big")
            return f"{b[0]}.{b[1]}.{b[2]}.{b[3]}"
        elif name == "firmware":
            b = int(val_hex, 16).to_bytes(6, "big")
            return f"{b[0]}.{b[1]} ({int.from_bytes(b[4:6],'little'):04d}-{b[3]:02d}-{b[2]:02d})"
        elif name == "device_search":
            return hex2str(val_hex)
        elif name == "machine_hours":
            # Device returns total minutes as a 32-bit integer
            # Return as float hours (required by SensorDeviceClass.DURATION)
            total_min = int(val_hex, 16)
            return round(total_min / 60, 1)
        elif name == "filter_timer_countdown":
            # 32-bit payload: [minutes, hours, days, reserved]
            # Some devices prepend zeros, so always parse from the last 4 bytes.
            b = int(val_hex, 16).to_bytes(max((len(val_hex) + 1) // 2, 4), "big")
            minutes = b[-4]
            hours = b[-3]
            days = b[-2]
            return f"{days}d {hours:02d}h {minutes:02d}m"
        elif name == "timer_counter":
            b = int(val_hex, 16).to_bytes(max(len(val_hex) // 2, 3), "big")
            return f"{b[-3]}h {b[-2]}m {b[-1]}s"
        elif name in ("boost_time", "humidity_treshold", "analogV_treshold", "analogV"):
            return val_int
        else:
            return val_int
    except Exception as e:
        _LOGGER.debug("Error decoding param 0x%04X: %s", param_id, e)
        return None


class AtmoFan:
    """Handles communication with the VENTS TwinFresh Atmo Mini ventilation unit."""

    def __init__(self, host: str, password: str, device_id: str, port: int = 4000):
        self._host      = host
        self._password  = password
        self._device_id = device_id
        self._port      = port
        self._timeout   = 2.0
        self.data: dict = {}

    def _send_recv(self, pkt: bytes) -> bytes | None:
        """Send UDP packet and return response, or None on timeout."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(self._timeout)
        try:
            sock.connect((self._host, self._port))
            sock.sendall(pkt)
            return sock.recv(1024)
        except socket.timeout:
            _LOGGER.debug("Timeout reading from %s", self._host)
            return None
        except Exception as e:
            _LOGGER.warning("Communication error: %s", e)
            return None
        finally:
            sock.close()

    def read_param(self, param_id: int):
        """Read a single parameter from the device."""
        param_hex = hex(param_id).replace("0x", "").zfill(4)
        pkt = build_packet(self._device_id, self._password, FUNC_READ, param_hex)
        resp = self._send_recv(pkt)
        if resp:
            results = parse_response(resp)
            for pid, val_hex in results.items():
                self.data[pid] = decode(pid, val_hex)
            return self.data.get(param_id)
        return None

    def write_param(self, param_id: int, value: int | str) -> bool:
        """Write a parameter to the device using pyEcoventV2 packet format.

        The protocol omits the high byte of the parameter ID when it is 0x00.
        Example: param 0x00b7 is encoded as 'b7', not '00b7'.
        """
        param_hex = hex(param_id).replace("0x", "").zfill(4)
        if isinstance(value, int):
            val_hex = hex(value).replace("0x", "").zfill(2)
        else:
            val_hex = str(value)

        val_bytes = len(val_hex) // 2 if val_hex else 0
        n_out = ""
        if param_hex[:2] != "00":
            # High byte prefix for parameters above 0x00FF
            n_out = "ff" + param_hex[:2]
        if val_bytes > 1:
            # Multi-byte value prefix
            n_out += "fe" + hex(val_bytes).replace("0x", "").zfill(2) + param_hex[2:4]
        else:
            n_out += param_hex[2:4]

        parameter = n_out + val_hex
        pkt = build_packet(self._device_id, self._password, FUNC_WRITE_RETURN, parameter)
        resp = self._send_recv(pkt)
        return resp is not None

    def update(self) -> bool:
        """Read all supported parameters from the device one by one.

        Note: TwinFresh Atmo Mini does not respond to bulk read-all requests,
        so each parameter must be queried individually.
        """
        success = 0
        for param_id in SUPPORTED_PARAMS:
            val = self.read_param(param_id)
            if val is not None:
                success += 1
            time.sleep(0.05)
        _LOGGER.debug("Updated %d/%d parameters", success, len(SUPPORTED_PARAMS))
        return success > 0

    # ── Properties ─────────────────────────────────────────────────────────────

    @property
    def state(self) -> str | None:
        return self.data.get(0x0001)

    @property
    def speed(self) -> str | None:
        return self.data.get(0x0002)

    @property
    def airflow(self) -> str | None:
        return self.data.get(0x00b7)

    @property
    def humidity(self) -> int | None:
        return self.data.get(0x0025)

    @property
    def fan1_speed(self) -> int | None:
        return self.data.get(0x004a)

    @property
    def fan2_speed(self) -> int | None:
        return self.data.get(0x004b)

    @property
    def man_speed(self) -> int | None:
        return self.data.get(0x0044)

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
        return self.data.get(0x00b8)

    @property
    def humidity_sensor_state(self) -> str | None:
        return self.data.get(0x000f)

    @property
    def relay_sensor_state(self) -> str | None:
        return self.data.get(0x0014)

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
        return self.data.get(0x007e)

    @property
    def filter_timer_countdown(self) -> str | None:
        return self.data.get(0x0064)

    @property
    def firmware(self) -> str | None:
        return self.data.get(0x0086)

    @property
    def curent_wifi_ip(self) -> str | None:
        return self.data.get(0x00a3)

    @property
    def unit_type(self) -> str | None:
        return self.data.get(0x00b9)

    @property
    def id(self) -> str:
        return self._device_id

    @property
    def name(self) -> str:
        return "TwinFresh Atmo Mini"

    # ── Commands ───────────────────────────────────────────────────────────────

    def turn_on(self) -> bool:
        return self.write_param(0x0001, 1)

    def turn_off(self) -> bool:
        return self.write_param(0x0001, 0)

    def set_speed(self, speed: str) -> bool:
        """Set fan speed: low=1, medium=2, high=3."""
        mapping = {"low": 1, "medium": 2, "high": 3, "manual": 0xff}
        val = mapping.get(speed)
        if val is None:
            return False
        return self.write_param(0x0002, val)

    def set_man_speed(self, percent: int) -> bool:
        """Set manual speed as percentage (1-100%). Switches device to manual mode."""
        val = math.ceil(255 / 100 * max(1, min(100, percent)))
        ok = self.write_param(0x0044, val)
        if ok:
            self.write_param(0x0002, 0xff)  # switch to manual mode
        return ok

    def set_airflow(self, mode: str) -> bool:
        """Set airflow mode: ventilation=0, heat_recovery=1, air_supply=2."""
        mapping = {"ventilation": 0, "heat_recovery": 1, "air_supply": 2}
        val = mapping.get(mode)
        if val is None:
            return False
        return self.write_param(0x00b7, val)

    def reset_filter_timer(self) -> bool:
        """Reset the filter replacement timer."""
        return self.write_param(0x0065, 0)

    def reset_alarms(self) -> bool:
        """Clear all active alarms."""
        return self.write_param(0x0080, 0)
