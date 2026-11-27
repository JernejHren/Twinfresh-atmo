# Changelog

## 0.3.0

- **UDP reliability & 3-tier polling:** Replaced connected socket-per-parameter UDP queries with a single `threading.Lock`-guarded `sendto`/`recvfrom` socket per poll, 1 quick retry on transient drops, early fast-fail on offline devices, and cached-state tolerance for brief MCU pauses (eliminating `[Errno 111] Connection refused` and periodic `unavailable` blips).
- **Reduced UDP traffic:** Split polling into 3 tiers — 10 fast live-telemetry parameters every `update_interval` (default 30s, configurable 10–600s), 10 slow config/counter parameters every 5 minutes (and immediately after writes/resets), and 3 static metadata parameters every 30 minutes.
- **Packet validation:** Added `FDFD` header, 16-bit little-endian checksum (`& 0xFFFF`), dynamic `device_id` length offset, and `FUNC_RESPONSE` (`0x06`) validation.
- **Bug fixes:**
  - Fixed `0x007e` (`machine_hours` / Operating Hours) decoding from 4-byte `[minutes, hours, days_lo, days_hi]` instead of big-endian total minutes.
  - Added missing `AtmoFan.relay_status` (`0x0032`) property so the Relay Status binary sensor updates instead of staying `unknown`.
  - Fixed `fan.set_percentage(0)` to turn the fan off instead of setting `"low"`.
  - Added `0x1B00` (`TwinFresh Atmo Mini`) to `unit_type` mapping.
  - Removed hardcoded `self.entity_id` overrides across platforms so Home Assistant manages entity IDs cleanly.
- **New features & UX:**
  - Added `"standby"` and `"manual"` speed/preset support plus a stepless `1–100%` Manual Speed `number` entity.
  - Added UI `OptionsFlow` (English and Slovenian translations) to update host, port, password, and polling interval without removing the integration.
  - Typed the `Alarm` sensor as `ENUM` with explicit options.
  - Added local Home Assistant `brand/` assets (`icon.png`, `icon@2x.png`, `logo.png`, `logo@2x.png`).

## 0.2.2

- Fixed filter countdown decoding and formatting to display consistent day/hour/minute values.
- Improved fan startup behavior when setting speed, so selecting preset/percentage while off now turns the device on first.
- Thanks to @ernestk84 for reporting the filter countdown issue and the missing power-on-with-speed behavior.
