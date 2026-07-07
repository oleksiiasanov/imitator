# VTX Video Control

## Quick Start

1. Write Raspberry Pi OS Lite to a microSD card with Raspberry Pi Imager.
2. In Imager settings, enable SSH and configure Wi-Fi for the network you will use.
3. Boot the Raspberry Pi and connect to it over SSH.
4. Clone or copy this project to the Raspberry Pi, for example to `/home/pi/imitator`.
5. Run the installer:

```bash
cd /home/pi/imitator
sudo bash install.sh
```

6. After the reboot, open the web panel:

```text
Wi-Fi: VTX-SETUP
Password: vtxplayer
URL: http://10.42.0.1:8080
```

Use the panel to upload a video, convert it for FPV playback, start or pause playback, and set autoplay timing.

## Hardware Requirements

- Raspberry Pi Zero 2 W.
- microSD card with Raspberry Pi OS Lite.
- Analog 5.8GHz VTX.
- VTX antenna.
- FPV receiver or SDR receiver.
- Logic-level MOSFET module for VTX/fan power switching.
- 5V USB power for initial setup.
- Step-down buck converter set to 5.1V if powering the Raspberry Pi from a flight battery later.
- Wires and soldering tools.

## Wiring

Connect the video signal and ground before powering the VTX.

```text
Raspberry Pi TV pad -> VTX VIDEO IN
Raspberry Pi GND    -> VTX GND
Raspberry Pi GPIO17 -> MOSFET control input
Battery +           -> MOSFET input
MOSFET output       -> VTX/fan power branch
Battery -           -> VTX GND / MOSFET GND
```

Important:

- Always connect the VTX antenna before powering the VTX.
- Do not power the Raspberry Pi directly from a 6S battery.
- Battery GND, VTX GND, and Raspberry Pi GND must be common.
- For first setup, power the Raspberry Pi from USB and power the VTX through the MOSFET branch.
- The Raspberry Pi controls only the MOSFET gate. It must not power the VTX directly.

## Installation and First Boot

Run the installer from the project directory:

```bash
sudo bash install.sh
```

The installer:

- Installs Python, Flask dependencies, FFmpeg, and MPV.
- Installs GPIO dependencies with apt: `gpiod`, `python3-gpiozero`, and `python3-lgpio`.
- Creates a project-local Python environment in `.venv` with access to apt-installed Python packages.
- Installs only web Python dependencies from `requirements.txt` into `.venv`.
- Creates the upload and video directories.
- Configures the Raspberry Pi Wi-Fi Access Point `VTX-SETUP`.
- Enables composite video output for the Raspberry Pi.
- Disables the graphical desktop/display manager when present so MPV can control DRM/Composite directly.
- Installs and enables the `vtx-player` systemd service using `.venv/bin/python`.
- Reboots automatically when hardware settings need to be applied.

After reboot, the web application starts automatically. Open:

```text
Wi-Fi: VTX-SETUP
Password: vtxplayer
URL: http://10.42.0.1:8080
```

Upload a video in the web panel. The app converts it to `video_fpv.mp4`, enables GPIO17 MOSFET power before playback, starts MPV on Composite-1, disables MOSFET power after stop/exit, and keeps the configured autoplay settings in `config.json`.

## Changing Wi-Fi Later

After `install.sh`, normal access uses the device Wi-Fi Access Point `VTX-SETUP`. Use this recovery section only if you intentionally need router-client Wi-Fi again or cannot reach the AP.

With the SD card inserted into a Mac, the visible boot partition is usually mounted as:

```text
/Volumes/bootfs
```

The file `/Volumes/bootfs/network-config` contains the Wi-Fi used during first boot. For an already booted system, use the FAQ section in `index.html`: it contains the verified cloud-init recovery flow using `network-config`, `meta-data`, `user-data`, and `cloudwifi.log` checks.
