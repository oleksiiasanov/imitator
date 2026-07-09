# Change: Prepare V1 Release Candidate

## Why
The project is moving from prototype toward a first release candidate. The current base supports Flask UI, upload, scheduler, FFmpeg conversion, MPV playback, and composite output, but V1 requires real GPIO relay/power-switch safety, first-boot reliability, release validation documents, and production-grade error handling.

## What Changes
- Implement real GPIO17 relay/power-switch control while keeping all GPIO access inside `gpio.py`.
- Ensure relay/power-switch output is disabled on playback stop, playback completion, application exit, service stop, reboot, SIGTERM, Ctrl+C, exceptions, and unexpected failures.
- Polish existing UI spacing, button states, upload/conversion progress, status messages, and mobile responsiveness without redesigning the layout.
- Review and harden first boot so the app is reachable immediately after `install.sh` and reboot.
- Replace generic/silent failures with user-friendly web-visible errors and journal logs.
- Perform final production readiness review for install, startup, and runtime failures.
- Add `RELEASE_CHECKLIST.md`.
- Add `TEST_PLAN.md` for non-project users.

## Impact
- Affected specs: release-candidate
- Affected code: `gpio.py`, `app.py`, `install.sh`, `requirements.txt`, `services/vtx-player.service`, `templates/`, `static/`, `PROJECT_CONTEXT.md`, `README.md`
- Affected docs: `RELEASE_CHECKLIST.md`, `TEST_PLAN.md`
- Hardware affected: GPIO17, relay-controlled VTX/fan branch

## Out of Scope
- Wi-Fi Access Point
- OTA update implementation
- New page redesign or new visual identity
- Multiple playlists
- New hardware beyond GPIO17 relay VTX/fan switching
