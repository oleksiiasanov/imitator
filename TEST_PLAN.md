# Test Plan

This test plan is written for a tester with no project knowledge. Mark each test as Pass or Fail.

## Test 1: Clean Install

Preconditions:

- Fresh Raspberry Pi OS Lite is flashed.
- SSH and Wi-Fi are configured.
- This repository is copied or cloned to the Raspberry Pi.

Steps:

1. Open a terminal over SSH.
2. Go to the project directory.
3. Run `sudo bash install.sh`.
4. Let the Raspberry Pi reboot if the installer requests it.

Expected result:

- Installer finishes with `Installation completed.`
- Installer prints Wi-Fi `VTX-SETUP`, password `vtxplayer`, and `http://10.42.0.1:8080`.
- `.venv`, `uploads/`, `videos/`, and `config.json` exist.
- `vtx-player.service` is enabled.
- After reboot, Web UI opens at `http://10.42.0.1:8080` from a device connected to `VTX-SETUP`.

Pass/Fail:

- [ ] Pass
- [ ] Fail

## Test 1A: Wi-Fi Access Point

Preconditions:

- `sudo bash install.sh` has completed.
- Raspberry Pi has rebooted.
- A phone or laptop with Wi-Fi is available.

Steps:

1. Open Wi-Fi settings on the phone or laptop.
2. Join `VTX-SETUP` using password `vtxplayer`.
3. Open `http://10.42.0.1:8080`.
4. Open `http://10.42.0.1:8080/system`.

Expected result:

- `VTX-SETUP` is visible.
- The browser device joins the AP successfully.
- Main web UI opens.
- `/system` shows Wi-Fi AP status.

Pass/Fail:

- [ ] Pass
- [ ] Fail

## Test 2: Upload

Preconditions:

- Web UI is open.
- A valid video file is available on the browser device.

Steps:

1. Select the video file.
2. Press the upload button.
3. Watch upload and conversion progress.

Expected result:

- Upload progress reaches 100%.
- Conversion progress reaches 100%.
- Success message appears.
- Playback starts after conversion.

Pass/Fail:

- [ ] Pass
- [ ] Fail

## Test 3: Overwrite Upload

Preconditions:

- One video has already been uploaded and converted.
- A second valid video file is available.

Steps:

1. Upload the second video.
2. Wait for conversion to finish.
3. Check `videos/video_fpv.mp4`.

Expected result:

- The old upload is removed from `uploads/`.
- `videos/video_fpv.mp4` is replaced by the converted second video.
- Playback starts using the new video.

Pass/Fail:

- [ ] Pass
- [ ] Fail

## Test 4: Playback

Preconditions:

- `videos/video_fpv.mp4` exists.
- `/system` shows MPV, ffmpeg, Composite, and GPIO17 as available.

Steps:

1. Press Play in the web UI.
2. Watch the FPV receiver.
3. Check MOSFET/GPIO17 state.

Expected result:

- GPIO17 turns on.
- MPV starts after the settle delay.
- Video is visible on the receiver.
- Web UI shows playback as running after refresh.

Pass/Fail:

- [ ] Pass
- [ ] Fail

## Test 5: Stop

Preconditions:

- Playback is running.

Steps:

1. Press Pause in the web UI.
2. Watch the FPV receiver.
3. Check MOSFET/GPIO17 state.

Expected result:

- MPV stops.
- GPIO17 turns off.
- VTX/fan power branch turns off.
- Web UI shows playback as stopped after refresh.

Pass/Fail:

- [ ] Pass
- [ ] Fail

## Test 6: Scheduler

Preconditions:

- A converted video exists.
- Web UI is open.

Steps:

1. Enable autoplay.
2. Set first delay to 1 minute.
3. Set repeat interval to 1 minute.
4. Save settings.
5. Reboot the Raspberry Pi.
6. Wait for playback.

Expected result:

- Settings persist in `config.json`.
- Scheduler starts automatically after reboot.
- Playback starts after the configured delay.
- Playback repeats after the configured interval.

Pass/Fail:

- [ ] Pass
- [ ] Fail

## Test 7: Reboot

Preconditions:

- Web UI is reachable.
- A converted video exists.

Steps:

1. Start playback.
2. Reboot the Raspberry Pi.
3. Wait for boot.
4. Open the web UI again.

Expected result:

- GPIO17 is not left on during reboot.
- Service starts automatically.
- Web UI is reachable.
- Saved settings are preserved.

Pass/Fail:

- [ ] Pass
- [ ] Fail

## Test 8: Power Loss

Preconditions:

- Web UI is reachable.
- A converted video exists.

Steps:

1. Start playback.
2. Disconnect Raspberry Pi power.
3. Restore power.
4. Open the web UI after boot.

Expected result:

- System boots without manual repair.
- Web UI becomes reachable.
- GPIO17 is off until playback is requested by user or scheduler.
- Saved settings are preserved.

Pass/Fail:

- [ ] Pass
- [ ] Fail

## Test 9: GPIO

Preconditions:

- GPIO17 is wired to the MOSFET control input.
- A tester can measure GPIO17 or observe MOSFET state.

Steps:

1. Open `/system`.
2. Confirm GPIO17 status.
3. Start playback.
4. Stop playback.

Expected result:

- `/system` reports GPIO17 available.
- GPIO17 changes to on during playback.
- GPIO17 changes to off after stop.
- GPIO errors are visible in `/system` if hardware/backend is unavailable.

Pass/Fail:

- [ ] Pass
- [ ] Fail

## Test 10: MOSFET

Preconditions:

- MOSFET branch is wired to VTX/fan power.
- VTX antenna is connected.

Steps:

1. Confirm the VTX/fan is off while idle.
2. Start playback.
3. Stop playback.
4. Stop the service with `sudo systemctl stop vtx-player`.

Expected result:

- VTX/fan power turns on only during playback.
- VTX/fan power turns off after stop.
- VTX/fan power turns off when the service stops.

Pass/Fail:

- [ ] Pass
- [ ] Fail

## Test 11: Invalid Video

Preconditions:

- Web UI is open.
- A non-video file is available.

Steps:

1. Select the non-video file.
2. Press upload.

Expected result:

- Browser rejects the file or server returns a clear error.
- Existing converted video is not replaced.
- Playback does not start.

Pass/Fail:

- [ ] Pass
- [ ] Fail

## Test 12: Large Video

Preconditions:

- Web UI is open.
- A large valid video under 4 GB is available.
- Enough free disk space is available.

Steps:

1. Upload the large video.
2. Wait for conversion.
3. Open `/system` and check free disk space.

Expected result:

- Upload progress is visible.
- Conversion progress is visible.
- Conversion completes or fails with a clear error.
- No silent failure occurs.

Pass/Fail:

- [ ] Pass
- [ ] Fail

## Test 13: Browser Refresh

Preconditions:

- A video upload or conversion is in progress.

Steps:

1. Refresh the browser page during conversion.
2. Wait for the page to reload.

Expected result:

- Conversion status continues to show.
- Playback button remains disabled while conversion is running.
- Final success or error message appears.

Pass/Fail:

- [ ] Pass
- [ ] Fail

## Test 14: Mobile Browser

Preconditions:

- Phone or tablet is connected to Wi-Fi `VTX-SETUP`.
- Web UI is reachable from that device at `http://10.42.0.1:8080`.

Steps:

1. Open the web UI on the mobile browser.
2. Open `/system`.
3. Upload a small valid video.
4. Start and stop playback.

Expected result:

- Text and buttons fit the screen.
- Upload and conversion status are visible.
- `/system` is readable.
- Playback controls work.

Pass/Fail:

- [ ] Pass
- [ ] Fail
