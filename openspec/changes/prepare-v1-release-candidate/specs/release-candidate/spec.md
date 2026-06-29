## ADDED Requirements

### Requirement: GPIO17 MOSFET Control
The system SHALL control MOSFET power through GPIO17 for VTX/fan power switching during playback.

#### Scenario: Power on before playback
- **WHEN** playback is requested manually, by upload auto-start, or by scheduler
- **THEN** the system SHALL call `gpio.power_on()`
- **AND** wait 300 ms before starting MPV.

#### Scenario: Power off after playback ends
- **WHEN** one-shot playback exits normally
- **THEN** the system SHALL call `gpio.power_off()`.

#### Scenario: GPIO isolation
- **WHEN** GPIO hardware is accessed
- **THEN** all GPIO backend imports and pin operations SHALL be contained in `gpio.py`.

### Requirement: Safe MOSFET Shutdown
The system SHALL disable MOSFET power whenever the application or playback exits unexpectedly or intentionally.

#### Scenario: Service stop
- **WHEN** systemd stops the service with SIGTERM
- **THEN** the application SHALL call `gpio.power_off()` before exit.

#### Scenario: Keyboard interrupt
- **WHEN** the application receives Ctrl+C/SIGINT during development
- **THEN** the application SHALL call `gpio.power_off()` before exit.

#### Scenario: Playback exception
- **WHEN** MPV start or playback raises an exception
- **THEN** the application SHALL call `gpio.power_off()`
- **AND** log the failure to the journal.

#### Scenario: Reboot or power loss recovery
- **WHEN** the device reboots after normal shutdown or power loss
- **THEN** GPIO initialization SHALL default MOSFET power to off.

### Requirement: Existing UI Polish
The system SHALL improve the current web UI without changing the layout or primary workflows.

#### Scenario: Upload and conversion feedback
- **WHEN** a user uploads a video
- **THEN** the UI SHALL show upload progress, conversion progress, conversion result, and clear errors.

#### Scenario: Disabled controls
- **WHEN** conversion is running
- **THEN** the UI SHALL disable controls that would start playback or conflict with conversion.

#### Scenario: Mobile browser
- **WHEN** the UI is opened on a mobile browser
- **THEN** controls and status text SHALL remain readable and usable without layout redesign.

### Requirement: First Boot Readiness
The system SHALL be reachable immediately after `install.sh` completes and the Raspberry Pi reboots.

#### Scenario: Clean install reboot
- **WHEN** a non-technical user runs `sudo bash install.sh` on clean Raspberry Pi OS and the device reboots if requested
- **THEN** the Flask web UI SHALL start automatically under systemd.

#### Scenario: Runtime permissions
- **WHEN** the service starts after reboot
- **THEN** `.venv`, `uploads/`, `videos/`, and `config.json` SHALL have permissions compatible with the service user.

#### Scenario: Startup order
- **WHEN** the system boots
- **THEN** the service SHALL wait for required network/system readiness before starting.

### Requirement: User Visible Error Handling
The system SHALL report runtime and installation failures clearly to the user and journal.

#### Scenario: Web-visible runtime failure
- **WHEN** upload, conversion, playback, scheduler, GPIO, MOSFET, or diagnostics fail
- **THEN** the failure SHALL be visible in the Web UI or API response
- **AND** logged to the journal.

#### Scenario: Installer failure
- **WHEN** installation fails
- **THEN** `install.sh` SHALL print a clear error with remediation guidance
- **AND** restore changed boot/service files where possible.

### Requirement: Production Readiness Review
The system SHALL undergo a production readiness review before V1 release.

#### Scenario: Non-technical clone and install
- **WHEN** the repository is cloned by a non-technical user
- **THEN** all installation, startup, and runtime failure points identified during review SHALL be fixed without adding unrelated features.

### Requirement: Release Checklist
The repository SHALL provide a release checklist for manual validation before V1 release.

#### Scenario: Checklist coverage
- **WHEN** `RELEASE_CHECKLIST.md` is opened
- **THEN** it SHALL cover fresh Raspberry Pi OS installation, `install.sh`, reboot, Wi-Fi, Web UI, upload, conversion, playback, scheduler, GPIO, MOSFET, shutdown, and power loss recovery.

### Requirement: Test Plan
The repository SHALL provide a test plan usable by a person with no project knowledge.

#### Scenario: Test format
- **WHEN** a test case appears in `TEST_PLAN.md`
- **THEN** it SHALL include Preconditions, Steps, Expected result, and Pass/Fail checkbox.

#### Scenario: Test coverage
- **WHEN** `TEST_PLAN.md` is reviewed
- **THEN** it SHALL cover clean install, upload, overwrite upload, playback, stop, scheduler, reboot, power loss, GPIO, MOSFET, invalid video, large video, browser refresh, and mobile browser.
