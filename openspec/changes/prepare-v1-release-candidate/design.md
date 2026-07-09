## Context
VTX Player currently has a stable prototype base with no-op GPIO methods. V1 RC introduces actual power switching through GPIO17 and a 5V relay module, which creates hardware safety requirements that are stricter than ordinary web application behavior.

## Goals / Non-Goals
Goals:
- Make relay/power-switch control deterministic and fail-safe.
- Keep GPIO implementation isolated in `gpio.py`.
- Preserve current upload, conversion, playback, scheduler, systemd, and composite behavior.
- Make first boot and install failures understandable to a non-technical user.
- Provide release validation documents that can be followed without project knowledge.

Non-Goals:
- Do not add Wi-Fi AP.
- Do not add OTA updates.
- Do not redesign the UI.
- Do not add playlist support or new playback features.

## Decisions
- Decision: Use GPIO17 as the only supported relay/power-switch control pin for V1 RC.
- Decision: Use a 5V relay module in HIGH trigger mode for the current validated hardware wiring.
- Decision: Keep all GPIO backend imports and pin operations inside `gpio.py`.
- Decision: Playback code calls `gpio.power_on()`, waits 300 ms, starts MPV, and calls `gpio.power_off()` in all stop/completion/error paths.
- Decision: Application shutdown hooks and signal handlers must call `gpio.power_off()`.
- Decision: `install.sh` owns installation of GPIO backend dependencies.
- Decision: UI polish is limited to spacing, button states, progress visibility, messages, and mobile responsiveness.
- Decision: Release checklist and test plan are mandatory deliverables before V1 release.

## Alternatives Considered
- Direct `RPi.GPIO`: rejected for V1 proposal because `gpiozero` or `lgpio` backend is preferred for modern Raspberry Pi OS compatibility.
- GPIO access from Flask routes: rejected because `gpio.py` must remain the only GPIO boundary.
- Large UI redesign: rejected because RC should stabilize existing behavior.

## Risks / Trade-offs
- Risk: GPIO backend differences between Raspberry Pi OS versions.
  Mitigation: install and document the chosen backend, and expose clear diagnostics when GPIO initialization fails.
- Risk: Relay/power-switch output stays on after crash or service stop.
  Mitigation: use `finally`, signal handlers, `atexit`, systemd stop behavior, and conservative GPIO default-off initialization.
- Risk: first boot failures are hard for non-technical users.
  Mitigation: installer checks, journal logs, `/system`, web-visible status, and release checklist validation.
- Risk: hardware tests cannot be fully simulated on Mac.
  Mitigation: include real hardware validation in `RELEASE_CHECKLIST.md` and `TEST_PLAN.md`.

## Migration Plan
1. Add GPIO backend dependency and real `gpio.py` implementation.
2. Wire playback lifecycle to GPIO power on/off with 300 ms settle delay.
3. Add shutdown and signal safety paths.
4. Harden first boot and installer behavior.
5. Polish UI without layout redesign.
6. Replace generic/silent failures with visible and logged errors.
7. Add release validation documents.
8. Update `PROJECT_CONTEXT.md`.

## Open Questions
- Final GPIO backend choice: `gpiozero` with lgpio backend, or direct `lgpio`.
- Whether VTX and fan share the same relay branch for V1 hardware validation.
- Whether the release version should become `1.0.0-rc.1` in `VERSION`.
