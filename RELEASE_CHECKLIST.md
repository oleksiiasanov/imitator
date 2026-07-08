# Release Checklist

Use this checklist before tagging or handing off a release candidate.

## Fresh Raspberry Pi OS

- [ ] Flash a fresh Raspberry Pi OS Lite image to a microSD card.
- [ ] Enable SSH and configure the target Wi-Fi network in Raspberry Pi Imager.
- [ ] Boot Raspberry Pi Zero 2 W and confirm SSH access works.
- [ ] Clone or copy this repository to the Raspberry Pi.
- [ ] Confirm the VTX antenna is connected before powering the VTX.
- [ ] Confirm Raspberry Pi GND, battery GND, VTX GND, and MOSFET GND share a common ground.

## Wiring

- [ ] Pi TV pad is connected to VTX VIDEO IN.
- [ ] Pi GND is connected to VTX GND.
- [ ] Pi GPIO17 is connected to the MOSFET control input.
- [ ] Battery positive feeds the MOSFET input.
- [ ] MOSFET output feeds the VTX/fan power branch.
- [ ] Raspberry Pi is powered from USB 5V or a 5.1V buck converter, not directly from battery voltage.

## install.sh

- [ ] Run `sudo bash install.sh` from the project directory.
- [ ] Installer detects Raspberry Pi OS and prints the install directory and app user.
- [ ] Installer installs apt packages without errors.
- [ ] Installer creates `.venv` inside the project.
- [ ] Installer creates `.venv` with system site packages enabled.
- [ ] Installer installs only Flask/Werkzeug from `requirements.txt` with pip.
- [ ] Installer installs `gpiod`, `python3-gpiozero`, and `python3-lgpio` with apt.
- [ ] Installer installs NetworkManager tooling for Wi-Fi AP mode.
- [ ] Installer configures NetworkManager connection `vtx-hotspot`.
- [ ] `pip install -r requirements.txt` does not build or install `gpiozero` or `lgpio`.
- [ ] Installer disables graphical desktop/display manager if present.
- [ ] No desktop compositor holds `/dev/dri/card0` during playback.
- [ ] Installer creates `uploads/`, `videos/`, and `config.json`.
- [ ] Installer installs and enables `vtx-player.service`.
- [ ] Installer stops an existing `vtx-player.service` before self-check so GPIO17 is not busy.
- [ ] Installer self-check reports ffmpeg, mpv, Wi-Fi AP, GPIO17, uploads, videos, and config.json as OK.
- [ ] Installer prints SSID `VTX-SETUP`, password `vtxplayer`, web URL, and journal command.
- [ ] Running `sudo bash install.sh` a second time succeeds without breaking the service.

## Reboot And First Boot

- [ ] Reboot after installation.
- [ ] `vtx-player.service` starts automatically after reboot.
- [ ] Wi-Fi network `VTX-SETUP` appears after reboot.
- [ ] Browser device can join `VTX-SETUP` using password `vtxplayer`.
- [ ] The web UI opens at `http://10.42.0.1:8080`.
- [ ] `/system` opens and is read-only.
- [ ] `/system` shows Wi-Fi/AP status clearly.
- [ ] Composite output status is shown clearly.
- [ ] GPIO17 status is shown clearly.
- [ ] MOSFET status is shown clearly.
- [ ] Journal logs include the application version and startup self-check.

## Wi-Fi

- [ ] Raspberry Pi provides Wi-Fi AP `VTX-SETUP` after reboot.
- [ ] AP assigns an address to a phone or laptop.
- [ ] Browser access works from a device connected to `VTX-SETUP`.
- [ ] Re-running `sudo bash install.sh` keeps AP access working.

## Web UI

- [ ] Main page loads on desktop browser.
- [ ] Main page loads on mobile browser.
- [ ] Diagnostics are visible on the main page.
- [ ] Upload controls are usable on desktop and mobile.
- [ ] Buttons show disabled state during conversion.
- [ ] Errors are visible in the page instead of failing silently.

## Upload And Conversion

- [ ] Upload a valid video.
- [ ] Upload progress is visible.
- [ ] Conversion progress is visible.
- [ ] Conversion success message is visible.
- [ ] Converted file exists at `videos/video_fpv.mp4`.
- [ ] Uploading a second valid video replaces the previous video.
- [ ] Invalid video type is rejected with a clear message.
- [ ] Large video within the 4 GB limit is accepted and converted.

## Playback

- [ ] Playback starts automatically after successful upload/conversion.
- [ ] Manual Play starts MPV playback on Composite-1.
- [ ] Manual Pause stops MPV playback.
- [ ] Playback cannot start while conversion is running.
- [ ] MPV failure is logged and visible as a web error or diagnostic failure.

## Scheduler

- [ ] Enable autoplay in the web UI.
- [ ] Save delay and interval settings.
- [ ] Reboot the Raspberry Pi.
- [ ] Scheduler starts after reboot when autoplay is enabled.
- [ ] Scheduler waits the configured delay.
- [ ] Scheduler plays the current video once.
- [ ] Scheduler waits the configured interval before repeating.
- [ ] Disabling autoplay stops future scheduled playback.

## GPIO And MOSFET

- [ ] GPIO17 is LOW when the app is idle.
- [ ] GPIO17 goes HIGH before MPV playback starts.
- [ ] Playback starts after the MOSFET settle delay.
- [ ] GPIO17 goes LOW after manual Pause.
- [ ] GPIO17 goes LOW after scheduled playback ends.
- [ ] GPIO17 goes LOW if MPV exits unexpectedly.
- [ ] GPIO17 goes LOW when `systemctl stop vtx-player` is run.
- [ ] GPIO17 goes LOW during reboot.
- [ ] GPIO17 goes LOW after application crash or Ctrl+C in foreground testing.

## Shutdown And Power Loss

- [ ] Reboot during idle state recovers cleanly.
- [ ] Reboot during playback recovers cleanly and does not leave MOSFET power enabled.
- [ ] Power loss during idle state recovers cleanly on next boot.
- [ ] Power loss during playback recovers cleanly on next boot.
- [ ] Web UI is reachable again after power returns.
- [ ] Autoplay behavior after power return matches saved `config.json`.

## Final Gate

- [ ] `python3 -m py_compile app.py gpio.py` passes.
- [ ] `bash -n install.sh` passes.
- [ ] OpenSpec validation passes for the release-candidate change.
- [ ] `PROJECT_CONTEXT.md` matches the current implementation.
- [ ] No TODOs, debug prints, temporary files, or obsolete documentation remain.
