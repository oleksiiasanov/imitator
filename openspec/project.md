# Project Context

## Purpose
VTX Player is a Raspberry Pi Zero 2 W analog FPV video playback controller. It provides a Flask web UI for uploading video, converting it with FFmpeg, and playing it through Raspberry Pi composite output with MPV.

`PROJECT_CONTEXT.md` is the single source of truth for current implementation details, roadmap boundaries, and definition of done.

## Tech Stack
- Python
- Flask / Werkzeug
- FFmpeg / FFprobe
- MPV
- systemd
- NetworkManager / nmcli
- Raspberry Pi OS Lite
- Raspberry Pi composite TV output
- Shell installer (`install.sh`)

## Project Conventions
- Keep implementation simple and boring.
- Prefer small incremental changes.
- Keep HTML in templates, JavaScript in `static/app.js`, and styles in `static/style.css`.
- Keep GPIO access isolated to `gpio.py`.
- Keep install and OS configuration in `install.sh`.
- Keep runtime settings in `config.json`.
- Keep version in `VERSION`.
- Update `PROJECT_CONTEXT.md` whenever architecture or behavior changes.

## Testing Strategy
- Validate Python syntax with `py_compile`.
- Validate installer syntax with `bash -n install.sh`.
- Use Flask test client for route behavior where hardware is not required.
- Validate GPIO/MOSFET, composite output, reboot, power loss, and first boot on real Raspberry Pi hardware before release.

## Important Constraints
- A non-technical user should not need terminal access after installation.
- `install.sh` must remain repeatable.
- The application must fail visibly in the web UI and journal, not silently.
- VTX power safety has priority over convenience.
- Do not add roadmap features unless explicitly requested.

## External Dependencies
- Raspberry Pi OS apt packages: Python, FFmpeg, MPV, systemd tooling, NetworkManager, `gpiod`, `python3-gpiozero`, and `python3-lgpio`.
- Python web dependencies are installed into project-local `.venv`.
- GPIO Python packages are not installed through pip; `.venv` uses system site packages to import apt-installed `gpiozero` and `lgpio`.
