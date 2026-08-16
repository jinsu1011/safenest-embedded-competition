# Historical ondevice_ai competition runtime copy

**Classification:** `HISTORICAL_REFERENCE` / `NOT_CURRENT_PI_RUNTIME`
**Archived:** 2026-08-16
**Source commit:** `0fc2fd5be40f3a5714e738258183676f4adb1109`
**Original active path:** `ondevice_ai/integrated_node/competition_runtime/`

This directory is an earlier copy of the Raspberry Pi LCD receiver, web dashboard,
installation script, and its test assets. It was preserved with `git mv` so its
history and original internal layout remain available for audit or comparison.

It is not the current Pi launch path. The current team Pi runtime is maintained in
`integration/` and is started through `integration/start_all.sh`; it does not import
this archived directory or `ondevice_ai/risk/`.

This archival move does not redesign risk weights, thresholds, emergency behavior,
AI models, preprocessing, or hardware code. It only removes a duplicate Pi-runtime
copy from the active AI component boundary.

Do not import this directory from active code. Any future comparison or recovery work
must be performed in an isolated branch and must not make this archive a runtime
fallback.

## Original package contents

- `raspberry_pi_lcd/`: ESP32 TCP receiver, LCD pages, thermal view, and GPIO buzzer control.
- `SafeNest_Web/`: administrator and guest web dashboard with the Raspberry Pi bridge.
- `install_raspberry_pi.sh` and `start_all.sh`: historical install and launch scripts.

The matching ESP32 sketch remains under
`devices/mmwave/firmware/competition_sensor_node/`; its current receiver/dashboard
documentation now points to `integration/` and `docs/competition_runtime/`.

## Original package README

The following text is retained from the original active location so the package's
historical operating instructions remain available without being mistaken for the
current runtime contract.

This directory contains the Raspberry Pi runtime from `SafeNest_GitHub_Package`.

- `raspberry_pi_lcd/`: ESP32 TCP receiver, LCD pages, thermal view, and GPIO buzzer control
- `SafeNest_Web/`: administrator and guest web dashboard with the Raspberry Pi bridge
- `install_raspberry_pi.sh`: installs both runtime applications into the Raspberry Pi home directory
- `start_all.sh`: starts the LCD receiver and web dashboard

Related files:

- ESP32 sketch: `devices/mmwave/firmware/competition_sensor_node/`
- Setup and protocol documentation: `docs/competition_runtime/`

Copy `SafeNest_Web/.env.example` to `.env` and
`devices/mmwave/firmware/competition_sensor_node/secrets.example.h` to `secrets.h`
only on the target machine. Never commit the resulting secret files.
