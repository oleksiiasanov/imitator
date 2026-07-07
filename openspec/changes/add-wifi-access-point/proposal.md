# Change: Add Wi-Fi Access Point

## Why
The device currently depends on an external router Wi-Fi configured during Raspberry Pi imaging. If the router changes or the field setup has no router, a non-technical user can lose access to the web UI and must edit the SD card.

## What Changes
- Configure the Raspberry Pi as its own Wi-Fi Access Point during `install.sh`.
- Use a deterministic SSID, password, and IP address so the web UI is reachable after reboot without an external router.
- Keep installation repeatable and recoverable.
- Expose AP status in `/system` and startup diagnostics.
- Update user documentation, release checklist, test plan, and project context.

## Impact
- Affected specs: `wifi-access-point`
- Affected code: `install.sh`, `app.py`, `templates/`, `README.md`, `PROJECT_CONTEXT.md`, `index.html`, `RELEASE_CHECKLIST.md`, `TEST_PLAN.md`
- Affected system: NetworkManager, wlan0, systemd startup order, first boot access URL

## Non-Goals
- No OTA updates.
- No web UI page for editing Wi-Fi settings.
- No simultaneous router-client and AP mode guarantee.
- No captive portal.
