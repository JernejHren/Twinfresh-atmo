# VENTS TwinFresh Atmo Mini — Home Assistant Integration

A custom integration for controlling the **VENTS TwinFresh Atmo Mini Wi-Fi** ventilation unit (recuperator) directly from Home Assistant over the local network, without any cloud dependency.

> **Tested on:** TwinFresh Atmo Mini Wi-Fi · Firmware 1.4 (2024-08-07) · unit_type `0x1a00`

---

## Features

- **Local polling** — communicates directly with the device over UDP, no cloud required
- **Full control:** turn on/off, set speed, set airflow mode
- **Sensors:** humidity, fan RPM, operating hours, filter status, alarm state, firmware, IP
- **Configuration:** humidity threshold, boost duration, analog voltage threshold
- **Buttons:** reset filter timer, reset alarms
- **Translations:** English, Slovenian

---

## Supported Entities

| Platform        | Entity                    | Description                                      |
|-----------------|---------------------------|--------------------------------------------------|
| `fan`           | Fan                       | On/off, speed (low/medium/high), airflow mode    |
| `select`        | Atmo Speed                | Fan speed: `low` / `medium` / `high`             |
| `select`        | Atmo Airflow              | Mode: `ventilation` / `heat_recovery` / `air_supply` |
| `sensor`        | Atmo Humidity             | Relative humidity (%)                            |
| `sensor`        | Atmo Fan 1 RPM            | Fan 1 speed in RPM                               |
| `sensor`        | Atmo Fan 2 RPM            | Fan 2 speed in RPM                               |
| `sensor`        | Atmo Operating Hours      | Total operating time (h)                         |
| `sensor`        | Atmo Filter Time Left     | Remaining time until filter replacement          |
| `sensor`        | Atmo Alarm                | Current alarm state                              |
| `sensor`        | Atmo Firmware             | Firmware version                                 |
| `sensor`        | Atmo WiFi IP              | Current device IP address                        |
| `binary_sensor` | Atmo Filter Replacement   | `on` = filter replacement required               |
| `binary_sensor` | Atmo Alarm                | `on` = active alarm                              |
| `binary_sensor` | Atmo Boost                | `on` = boost mode active                         |
| `binary_sensor` | Atmo Cloud Connection     | `on` = connected to VENTS cloud                  |
| `switch`        | Atmo Humidity Sensor      | Enable/disable humidity sensor input             |
| `switch`        | Atmo Relay Sensor         | Enable/disable relay sensor input                |
| `switch`        | Atmo Analog V Sensor      | Enable/disable analog voltage sensor input       |
| `number`        | Atmo Humidity Threshold   | Trigger threshold for humidity sensor (%)        |
| `number`        | Atmo Boost Duration       | Boost mode duration (min)                        |
| `number`        | Atmo Analog V Threshold   | Trigger threshold for analog voltage sensor      |
| `button`        | Atmo Reset Filter Timer   | Resets the filter replacement countdown          |
| `button`        | Atmo Reset Alarms         | Clears all active alarms                         |

---

## How It Works

The TwinFresh Atmo Mini communicates over **UDP port 4000** using the [pyEcoventV2](https://github.com/gody01/pyEcoventV2) protocol. This integration implements the protocol directly with no external library dependency.

**Important quirks discovered during development:**

- The device does **not** respond to bulk read-all requests — each parameter must be queried individually.
- Write packets must omit the high byte of the parameter ID when it is `0x00` (e.g. `0x00b7` is encoded as `b7`, not `00b7`). This differs from what you might expect and caused airflow writes to silently fail.

**Phase-pair operation:** The TwinFresh Atmo Mini is typically installed in pairs. The two units alternate direction every ~70 seconds to recover heat while continuously exchanging air. Only the **primary unit** (master) needs to be added to Home Assistant — the secondary unit follows automatically.

---

## Installation

### Manual

1. Download the latest release ZIP from the [Releases](../../releases) page.
2. Extract and copy the `twinfresh_atmo` folder into your Home Assistant `config/custom_components/` directory:
   ```
   config/
   └── custom_components/
       └── twinfresh_atmo/
           ├── __init__.py
           ├── atmo_fan.py
           ├── ...
   ```
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration** and search for **TwinFresh Atmo Mini**.

### HACS (manual repository)

1. In HACS, go to **Integrations → ⋮ → Custom repositories**.
2. Add this repository URL and select category **Integration**.
3. Install and restart Home Assistant.

---

## Configuration

During setup you will be asked for:

| Field       | Description                                               | Default |
|-------------|-----------------------------------------------------------|---------|
| IP address  | Local IP of the device (assign a static lease in router)  | —       |
| Password    | Device password                                           | `1111`  |
| Device ID   | Found in the VENTS app device list (e.g. `002C004A4B465718`) | —    |
| Port        | UDP port                                                  | `4000`  |

**Finding the Device ID:** Open the VENTS app → Device list. The ID is shown below the device name.

---

## Protocol Notes

Packet structure (hex string):

```
FDFD + 02 + [id_len][device_id] + [pwd_len][password] + [func] + [params] + [checksum]
```

- `FDFD` — fixed header
- `02` — packet type (client)
- Function codes: `01` = read, `03` = write with response
- Checksum: sum of all payload bytes, 16-bit little-endian

---

## Compatibility

| Device                        | Status       |
|-------------------------------|--------------|
| TwinFresh Atmo Mini Wi-Fi     | ✅ Tested     |
| Vento V.2 | Blauberg | same protocol, fully supported |


Other devices using the pyEcoventV2 protocol may work. Please open an issue with your `unit_type` value if you test on a different device.

---

## Contributing

Pull requests and issues are welcome. If you test this integration on a device not listed above, please open an issue with:
- Device model name
- `unit_type` hex value (visible in HA diagnostics)
- Firmware version
- Which entities work and which do not

---

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

---

## Acknowledgements

Protocol based on [pyEcoventV2](https://github.com/gody01/pyEcoventV2) by [@gody01](https://github.com/gody01).
