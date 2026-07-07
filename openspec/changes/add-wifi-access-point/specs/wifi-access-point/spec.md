## ADDED Requirements

### Requirement: Installer Configures Device Access Point
The installer SHALL configure the Raspberry Pi as a Wi-Fi Access Point for direct browser access without an external router.

#### Scenario: Clean install configures AP
- **WHEN** a user runs `sudo bash install.sh` on supported Raspberry Pi OS
- **THEN** the installer SHALL create or update a NetworkManager AP connection for `wlan0`
- **AND** the AP SHALL use SSID `VTX-SETUP`
- **AND** the AP SHALL use IP address `10.42.0.1`.

#### Scenario: Re-running installer is safe
- **WHEN** `sudo bash install.sh` is run again
- **THEN** the AP connection SHALL be updated idempotently
- **AND** unrelated user Wi-Fi profiles SHALL NOT be deleted.

### Requirement: First Boot Web UI Access
The system SHALL make the web UI reachable through the AP after installation and reboot.

#### Scenario: User opens web UI from AP
- **WHEN** the user connects a phone or laptop to `VTX-SETUP`
- **THEN** the user SHALL be able to open `http://10.42.0.1:8080`
- **AND** the existing upload, conversion, playback, scheduler, and system pages SHALL remain unchanged in behavior.

### Requirement: AP Status Visibility
The system SHALL expose Wi-Fi AP status clearly.

#### Scenario: AP is available
- **WHEN** `/system` is opened
- **THEN** it SHALL show Wi-Fi/AP availability, configured SSID, connection name, interface, and IP address where available.

#### Scenario: AP setup failed
- **WHEN** NetworkManager, `nmcli`, `wlan0`, or AP configuration is unavailable
- **THEN** `/system` and startup logs SHALL show a clear AP error instead of failing silently.

### Requirement: AP Documentation
The project documentation SHALL describe AP-based access as the normal post-install path.

#### Scenario: Non-technical user follows docs
- **WHEN** a first-time user reads the Quick Start or full instruction page
- **THEN** the docs SHALL tell them to connect to `VTX-SETUP`
- **AND** open `http://10.42.0.1:8080`
- **AND** include recovery guidance for router-client Wi-Fi only as troubleshooting.
