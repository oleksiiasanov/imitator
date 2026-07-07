# VTX Player

## Purpose

This repository contains a Raspberry Pi Zero 2 W based analog FPV video playback controller.

The current system lets a first-time Raspberry Pi user:

1. Flash Raspberry Pi OS Lite.
2. Copy or clone this project to the Raspberry Pi.
3. Run one installation script.
4. Open the web UI from a browser.
5. Upload a video.
6. Convert it automatically with FFmpeg.
7. Play it through Raspberry Pi composite output using MPV.

No manual Linux configuration should be required after `install.sh` completes.

The repository also contains `index.html`, the production static instruction page for assembling, installing, and validating the device. That page must describe the current implementation only. Do not document planned Wi-Fi AP or OTA behavior as already available.

---

## Main Goal

This project prioritizes:

* reliability
* simplicity
* maintainability
* repeatable installation
* understandable errors for non-Linux users

NOT:

* clever code
* complex architecture
* micro-optimizations
* premature hardware abstractions

If a simpler solution exists, prefer it.

---

## Hardware

Current supported hardware:

* Raspberry Pi Zero 2 W
* Raspberry Pi OS Lite, 64-bit preferred
* Analog 5.8GHz VTX
* VTX antenna
* FPV receiver or SDR receiver
* Buck converter set to 5.1V if powering Raspberry Pi from a battery
* Composite video output from the Raspberry Pi TV pad
* Logic-level MOSFET module controlled from GPIO17 for VTX/fan power switching

Planned hardware support:

* 6S Li-Ion battery powered autonomous setup

Future hardware support must remain backward compatible with the current composite playback flow.

---

## Electrical Architecture

Current implementation:

Battery or external power feeds the VTX through a logic-level MOSFET branch according to the VTX hardware requirements.

The Raspberry Pi is powered separately from USB 5V during setup, or from a buck converter set to 5.1V in an autonomous build.

The Raspberry Pi controls only the MOSFET gate on GPIO17. The Raspberry Pi must never power the VTX directly.

Required current wiring:

```text
Raspberry Pi TV pad -> VTX VIDEO IN
Raspberry Pi GND    -> VTX GND
GPIO17              -> MOSFET control input
Battery +           -> MOSFET input
MOSFET output       -> VTX/fan power branch
Battery -           -> VTX GND / MOSFET GND
```

Important:

All grounds must share a common reference.

```text
Battery GND = Raspberry Pi GND = VTX GND
```

MOSFET architecture:

```text
Battery
├── Buck Converter -> Raspberry Pi
└── MOSFET -> VTX and Cooling Fan
```

The Raspberry Pi role is to control only the MOSFET gate. The Raspberry Pi must never power the VTX directly.

---

## Wiring

Current required wiring:

```text
Pi TV OUT -> VTX VIDEO IN
Pi GND    -> VTX VIDEO GND / VTX GND
Pi GPIO17 -> MOSFET control input
```

VTX power depends on the specific VTX module. If the VTX supports VBAT/6S, it may be powered from the battery according to its datasheet.

The Raspberry Pi must not be powered directly from 6S. Use a 5.1V buck converter when running from a battery.

MOSFET wiring:

```text
GPIO17 -> MOSFET control input
MOSFET output -> VTX and fan power branch
```

---

## Power Sequence

Current runtime behaviour:

```text
Raspberry Pi boots
-> systemd starts Flask app
-> user opens web UI
-> user uploads video
-> FFmpeg converts it to videos/video_fpv.mp4
-> user presses Play or upload auto-starts playback
-> GPIO17 enables MOSFET power
-> app waits 300 ms for hardware to settle
-> MPV plays video on Composite-1
-> playback stop/exit disables GPIO17 MOSFET power
```

Autoplay uses the same playback function as manual one-shot playback. The scheduler controls timing only.

Current GPIO behaviour:

`gpio.power_on()` and `gpio.power_off()` control GPIO17 through `gpiozero` with the `lgpio` backend where available.

MOSFET power sequence:

```text
User presses Play or scheduler requests playback
-> GPIO17 HIGH
-> MOSFET ON
-> fan ON
-> VTX ON
-> short hardware settle delay
-> MPV starts playback
-> playback ends or is stopped
-> GPIO17 LOW
-> MOSFET OFF
```

Application exit, service stop, SIGTERM, SIGINT, MPV exit, playback stop, and startup failures all attempt to force GPIO17 LOW.

---

## Software Components

Current stack:

* Python
* Flask
* Werkzeug
* FFmpeg
* MPV
* gpiozero
* lgpio
* systemd
* Raspberry Pi composite TV output
* JavaScript upload progress in `static/app.js`
* CSS styling in `static/style.css`
* Static production instruction page in root `index.html`
* SD-card Wi-Fi recovery FAQ in `index.html` and a README pointer for already installed systems that no longer join the router Wi-Fi; the verified recovery path uses cloud-init `network-config`, `meta-data`, `user-data`, and `cloudwifi.log`

Current Python modules/files:

* `app.py` owns Flask routes, config persistence, diagnostics, upload, conversion, playback, and scheduler.
* `gpio.py` owns GPIO17/MOSFET control and all GPIO backend details.
* `templates/index.html` owns the web UI HTML.
* `static/app.js` owns upload progress and AJAX upload behaviour.
* `install.sh` owns OS detection, OS package install, `.venv` setup, composite boot configuration, runtime directories, service install, and self-check.
* `services/vtx-player.service` is the systemd unit template.
* `config.json` stores runtime settings.
* `VERSION` stores the current application version displayed in the UI, `/system`, and startup logs.
* `.gitignore` excludes `.venv`, local `venv`, Python caches, runtime upload/video artifacts, local `config.json`, logs, `.DS_Store`, and sample `video.mp4`.
* `openspec/` stores spec-driven change proposals and release-candidate planning.
* root `index.html` owns the public interactive instruction/checklist page and must remain synchronized with this document.

Future:

* Wi-Fi Access Point
* Logs page
* Health monitoring
* OTA or remote update flow

---

## Repository Philosophy

Repository represents the complete Raspberry playback system.

It is not only a Flask application.

The Flask application is one component of:

* operating system configuration
* composite video setup
* FFmpeg conversion
* MPV playback
* systemd autostart
* browser-based operation

---

## Installation Philosophy

Installation must be automatic and repeatable.

User should never manually edit:

* `config.txt`
* `cmdline.txt`
* systemd service files

Current `install.sh` owns:

* apt package installation
* Raspberry Pi OS detection from `/etc/os-release`
* Python virtualenv creation inside the project at `.venv` with `--system-site-packages`
* Python web dependency installation into `.venv`
* GPIO Python dependency installation only through apt packages: `python3-gpiozero` and `python3-lgpio`
* runtime directory creation
* `config.json` creation and ownership
* Raspberry Pi composite boot configuration
* graphical desktop/display manager disablement when present, because MPV DRM playback needs DRM master access
* systemd service installation and enablement
* systemd configuration to run `.venv/bin/python`
* GPIO package installation for GPIO17/MOSFET control through apt: `gpiod`, `python3-gpiozero`, and `python3-lgpio`
* application self-check
* clear success/failure output
* rollback for boot config and service file when possible

Current `install.sh` does not configure:

* Wi-Fi Access Point
* `hostapd`
* `dnsmasq`

Those are planned future features.

---

## Runtime Flow

Current browser flow:

```text
Browser
-> Upload
-> Flask /upload
-> FFmpeg
-> videos/video_fpv.mp4
-> MPV
-> Composite-1
-> Analog VTX
```

Current `/upload` behaviour:

* accepts a file field named `video`
* validates the uploaded filename extension
* removes old files from `uploads/`
* saves the new upload
* starts a background FFmpeg conversion job
* updates in-memory conversion status for the browser
* returns JSON success when upload is complete and conversion has started, or a clear JSON error
* starts MPV loop playback after successful conversion

Current `/upload-status` behaviour:

* returns read-only JSON conversion status
* reports conversion phase, percent, message, error, and filename
* is polled by `static/app.js` after upload completes

Current `/toggle` behaviour:

* if MPV is running, stop it
* otherwise start loop playback if diagnostics pass, no conversion is running, and video exists

Current `/settings` behaviour:

* saves autoplay enabled/disabled
* saves first delay in seconds
* saves interval in seconds
* restarts the scheduler generation

---

## Configuration

Runtime configuration is stored in `config.json`.

Current keys:

```json
{
  "autoplay_enabled": false,
  "start_delay_seconds": 0,
  "interval_seconds": 1200
}
```

`app.py` normalizes config values and writes `config.json` atomically using a temporary file plus `os.replace`.

Only user-editable runtime settings belong in `config.json`.

Implementation constants that are not user settings currently live in code or install script:

* upload limit: 4 GB
* converted output path: `videos/video_fpv.mp4`
* FFmpeg profile: 640x480, 30 fps, H.264, ultrafast, 1500k, no audio
* MPV connector: `Composite-1`
* DRM device: `/dev/dri/card0`
* composite boot mode: PAL `720x576@50e`

If these become user-facing options later, move them into config with defaults and migration.

---

## Web Interface

The web interface is the only runtime user interface.

After installation and first boot, normal operation should not require SSH.

Current primary functions:

* Application version display
* Upload video
* Replace current video
* File validation before upload
* Upload progress display
* Conversion progress display
* Conversion result and clear error display
* Runtime error banner for playback/self-check failures after redirects
* Play / pause
* Autoplay scheduler settings
* Startup diagnostics display
* Read-only `/system` status page

Current diagnostics shown in the web UI:

* `ffmpeg`
* `mpv`
* `Composite-1`
* `GPIO17`
* `uploads`
* `videos`
* `config.json`

Current `/system` status page shows:

* application version read from `VERSION`
* Python version
* Flask version
* `ffmpeg` availability
* `mpv` availability
* current video file status
* Composite output status
* free disk space
* application uptime
* GPIO17 availability, backend, and current power state
* MOSFET power switching availability and current state

Future UI features:

* Logs
* Temperature
* Wi-Fi/AP status

---

## Scheduler

Scheduler controls playback timing only.

Scheduler never manipulates GPIO directly.

Scheduler requests playback through `play_video_once()`.

Current implementation:

* scheduler runs in a daemon thread
* scheduler generation cancels older scheduler loops
* settings save restarts the scheduler generation
* autoplay is started on app boot if `config.json` enables it

---

## GPIO

GPIO implementation must remain isolated.

Only `gpio.py` may access Raspberry GPIO.

No Flask route should manipulate Raspberry GPIO directly.

Current implementation:

```python
def power_on():
    ...

def power_off():
    ...
```

`gpio.py` initializes GPIO17 as off, uses `gpiozero`, prefers the `lgpio` backend, exposes status for diagnostics, and keeps all GPIO exceptions out of Flask route code.

Future backend changes must remain inside `gpio.py` without changing Flask routes or playback code.

---

## Composite Video

Composite output is mandatory for the current product.

Current runtime output:

```text
Composite-1
```

Current install configuration:

* `enable_tvout=1`
* `sdtv_mode=2`
* `disable_overscan=1`
* `hdmi_ignore_hotplug=1`
* `dtoverlay=vc4-kms-v3d,composite=1`
* `video=Composite-1:720x576@50e`

The application must never modify boot configuration during runtime.

Boot configuration belongs to `install.sh`.

---

## Self Diagnostics

Application startup and the web UI use `collect_diagnostics()`.

Current checks:

* `ffmpeg` command exists
* `mpv` command exists
* `/sys/class/drm/...Composite-1/status` exists and is connected
* GPIO17/MOSFET control is available
* upload directory exists and is writable
* video directory exists and is writable
* `config.json` can be read and written

Diagnostics are displayed in the web UI. Startup diagnostics are logged.

Upload and toggle actions are blocked when diagnostics fail.

---

## Error Handling

Never fail silently.

Every operational error should:

* be logged where possible
* appear in the web UI or upload JSON response where possible
* provide a suggested fix whenever possible

Current known behaviour:

* Upload errors return JSON.
* FFmpeg errors return JSON and are logged.
* MPV process start errors return JSON or are logged.
* GPIO/MOSFET errors are logged, shown in diagnostics, and block playback.
* Playback and self-check errors after redirects are shown in the web UI runtime error banner.
* Diagnostics failures are visible in the browser.
* Install failures print a clear error and restore modified boot/service files where possible.

---

## Logging

Current log categories in `app.py`:

* application version at startup
* startup self-check
* upload received
* conversion progress/result
* FFmpeg conversion success/failure
* MPV start failure
* GPIO17/MOSFET power on/off
* application shutdown and signal cleanup
* scheduler restart
* settings save
* playback skipped because video is missing

Runtime logs are available through systemd:

```bash
journalctl -u vtx-player -f
```

Future log categories:

* Network
* temperature/health
* update flow

---

## Systemd

The app is managed by `vtx-player.service`.

Current service behaviour:

* runs under the install user, usually `pi`
* uses the project-local `.venv/bin/python`
* relies on `.venv` being created with system site packages so apt-installed `gpiozero` and `lgpio` are importable
* starts after `network-online.target`
* sets `PYTHONUNBUFFERED=1`
* sets `GPIOZERO_PIN_FACTORY=lgpio`
* verifies `.venv/bin/python` and `app.py` before start
* restarts on failure
* waits 5 seconds between restarts
* sends SIGTERM on stop so the app can disable MOSFET power
* uses a 10 second stop timeout
* uses `vtx-player` as the journal/syslog identifier
* writes stdout and stderr to journal
* is enabled by `install.sh`

MPV DRM playback requires direct DRM master access. On Raspberry Pi OS Desktop, `lightdm`/desktop compositors such as `labwc` can hold `/dev/dri/card0` and make MPV fail with `Failed to acquire DRM master: Permission denied`. `install.sh` therefore switches the system default to `multi-user.target` and disables common display manager services when present.

Every long-running production process must run under systemd.

---

## Design Rules

Always prefer simple code.

Never duplicate logic.

Use `pathlib` for project file paths in Python.

Never place HTML inside Python.

Keep `install.sh` idempotent.

Everything must survive reboot.

Everything must work after power loss.

One responsibility per module, but do not split files just because they become large.

Every long-running process must run under systemd.

Never require manual Linux configuration after installation.

When implementation changes, update this `PROJECT_CONTEXT.md` in the same commit.

Treat this file as mandatory context before making code changes.

Use OpenSpec for release candidates, new capabilities, architecture changes, hardware behavior changes, installation changes, and safety-critical work.

---

## AI Development Rules

Any AI agent modifying this project must preserve the following priorities:

1. Reliability
2. Simplicity
3. Easy installation
4. Hardware safety
5. Backward compatibility

AI should prefer small incremental changes.

Do not redesign the project unless explicitly requested.

Do not introduce unnecessary abstractions.

Do not add Wi-Fi AP, logs page, health monitoring, or other roadmap features unless explicitly requested.

Every new feature must preserve existing behaviour.

If implementation differs from this document, either fix the implementation or update this document so they match.

---

## Definition of Done

A change is complete only if:

* `install.sh` remains repeatable
* reboot succeeds on Raspberry Pi
* web interface still loads
* upload still works
* FFmpeg conversion still works
* MPV playback still works
* scheduler still works
* GPIO17/MOSFET power switching works and fails safely
* diagnostics still show clear status
* no manual Linux configuration is required after installation
* `PROJECT_CONTEXT.md` is updated when architecture or behaviour changes

---

## Future Roadmap

Planned features:

* Wi-Fi Access Point
* Logs page
* Temperature display
* OTA update
* Health monitoring
* Multiple video playlists
* Remote update
* Backup/restore configuration

Roadmap items are not current implementation.

---

## Current Project Status

Development stage:

```text
Release Candidate
```

Hardware status:

```text
Tested on Raspberry Pi Zero 2 W
```

Current version is `1.0.0-rc.1`, a release candidate for composite-video playback with GPIO17/MOSFET power switching.

The current system supports:

Implemented:

* Flask web UI
* application version from `VERSION`
* upload
* scheduler/autoplay
* FFmpeg conversion
* MPV playback on `Composite-1`
* Raspberry Pi composite output configured by `install.sh`
* `config.json` persistence
* startup/web self-diagnostics
* read-only `/system` status page
* GPIO17 control through `gpio.py`
* MOSFET power on/off around MPV playback
* safe MOSFET shutdown on stop, process exit, SIGTERM, SIGINT, and MPV exit
* systemd autostart and restart
* repeatable installation through `install.sh`
* project-local Python virtual environment at `.venv`

Planned:

* Wi-Fi Access Point
* OTA updates
* dedicated logs/health page beyond the current `/system` status page
* temperature display

The long-term goal is that the entire device can be deployed by executing:

```bash
git clone <repo>
cd <repo>
sudo bash install.sh
```

and then rebooting if the installer requests it.

No additional manual Linux configuration should be necessary.
