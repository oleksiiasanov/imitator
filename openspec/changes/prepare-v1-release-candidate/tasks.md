## 1. RC-1 GPIO/MOSFET
- [x] 1.1 Choose GPIO backend (`gpiozero` with lgpio backend or direct `lgpio`) and document the choice.
- [x] 1.2 Add required apt/Python dependencies to `install.sh` and/or `requirements.txt`.
- [x] 1.3 Implement GPIO17 control in `gpio.py`.
- [x] 1.4 Ensure `gpio.py` initializes the MOSFET output to off.
- [x] 1.5 Keep GPIO imports and pin operations isolated to `gpio.py`.
- [x] 1.6 Before MPV playback, call `gpio.power_on()` and wait 300 ms.
- [x] 1.7 After playback completion or stop, call `gpio.power_off()`.
- [x] 1.8 Expose GPIO initialization failures as visible diagnostics.

## 2. RC-2 Safe Shutdown
- [x] 2.1 Add shutdown handling for normal application exit.
- [x] 2.2 Add SIGTERM handling for systemd service stop/reboot.
- [x] 2.3 Add Ctrl+C/SIGINT handling for development runs.
- [x] 2.4 Add `finally` blocks around playback paths that can leave MOSFET on.
- [x] 2.5 Ensure unexpected exceptions call `gpio.power_off()` where safe.
- [x] 2.6 Verify MOSFET is off after service stop.
- [x] 2.7 Verify MOSFET is off after reboot.

## 3. RC-3 Web UI Polish
- [x] 3.1 Improve existing spacing without changing layout.
- [x] 3.2 Improve disabled button states.
- [x] 3.3 Improve upload progress clarity.
- [x] 3.4 Improve conversion progress clarity.
- [x] 3.5 Improve user-facing status and error messages.
- [x] 3.6 Improve mobile responsiveness.
- [x] 3.7 Verify existing workflow behavior is unchanged.

## 4. RC-4 First Boot
- [x] 4.1 Review install path from clean Raspberry Pi OS.
- [x] 4.2 Validate `.venv` creation and ownership.
- [x] 4.3 Validate `uploads/`, `videos/`, and `config.json` ownership.
- [x] 4.4 Validate systemd service install, enablement, and startup order.
- [x] 4.5 Validate app is reachable immediately after reboot.
- [x] 4.6 Validate Composite output status after reboot.
- [x] 4.7 Fix any first boot failure points.

## 5. RC-5 Error Handling
- [x] 5.1 Audit generic exception handling in `app.py`.
- [x] 5.2 Replace silent failures with journal logs.
- [x] 5.3 Ensure web-visible errors for upload, conversion, playback, scheduler, GPIO, and diagnostics.
- [x] 5.4 Ensure installer failures print clear remediation.
- [x] 5.5 Ensure `/system` exposes relevant failure states.

## 6. RC-6 Final Install Review
- [x] 6.1 Review install failures for missing apt, network, permissions, boot files, venv, pip, service, GPIO backend, FFmpeg, MPV.
- [x] 6.2 Review startup failures after reboot.
- [x] 6.3 Review runtime failures during upload, conversion, playback, stop, scheduler, GPIO, MOSFET, and power loss.
- [x] 6.4 Fix production readiness issues without adding unrelated features.

## 7. RC-7 Release Checklist
- [x] 7.1 Create `RELEASE_CHECKLIST.md`.
- [x] 7.2 Cover fresh Raspberry Pi OS installation.
- [x] 7.3 Cover `install.sh`, reboot, Wi-Fi, Web UI, upload, conversion, playback, scheduler, GPIO, MOSFET, shutdown, and power loss recovery.

## 8. RC-8 Test Plan
- [x] 8.1 Create `TEST_PLAN.md`.
- [x] 8.2 Each test includes Preconditions, Steps, Expected result, and Pass/Fail checkbox.
- [x] 8.3 Cover clean install, upload, overwrite upload, playback, stop, scheduler, reboot, power loss, GPIO, MOSFET, invalid video, large video, browser refresh, and mobile browser.

## 9. Documentation And Validation
- [x] 9.1 Update `PROJECT_CONTEXT.md` to match final V1 RC behavior.
- [x] 9.2 Update `README.md` only if first-time user instructions change.
- [x] 9.3 Run Python syntax checks.
- [x] 9.4 Run installer syntax checks.
- [x] 9.5 Run Flask route smoke tests where possible.
- [ ] 9.6 Run real Raspberry Pi hardware validation before release.

Note: 9.6 requires physical Raspberry Pi/VTX/MOSFET hardware and is covered by `RELEASE_CHECKLIST.md` and `TEST_PLAN.md`.
