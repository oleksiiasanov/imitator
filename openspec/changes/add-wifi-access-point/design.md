## Context
The project targets Raspberry Pi OS Lite on Raspberry Pi Zero 2 W. The latest Raspberry Pi OS releases use NetworkManager by default. The current app starts under systemd and binds Flask to `0.0.0.0:8080`.

## Goals
- After `sudo bash install.sh` and reboot, the user can connect to the device Wi-Fi and open the web UI.
- The AP setup is repeatable and idempotent.
- The AP has a stable browser URL: `http://10.42.0.1:8080`.
- Failures are visible in installer output, journal logs, and `/system`.

## Non-Goals
- The device does not need internet access while in AP mode.
- The device does not need to bridge or route internet traffic to clients.
- The web UI will not edit AP SSID/password in this change.

## Decisions
- Use NetworkManager `nmcli` rather than raw `hostapd` and `dnsmasq` configuration. This matches Raspberry Pi OS Trixie/Bookworm defaults and keeps rollback/idempotency simpler.
- Create a single AP connection named `vtx-hotspot` on `wlan0`.
- Use SSID `VTX-SETUP`, password `vtxplayer`, and IPv4 address `10.42.0.1/24`.
- Use `ipv4.method shared` so NetworkManager provides local DHCP for connected clients.
- Disable IPv6 for the AP connection.
- Prefer 2.4GHz band because Raspberry Pi Zero 2 W does not support 5GHz Wi-Fi.

## Risks / Trade-offs
- Some Raspberry Pi OS images may not have NetworkManager enabled. Mitigation: install/check NetworkManager packages and fail visibly if `nmcli` cannot configure AP mode.
- If a user expected router-client Wi-Fi, AP mode takes over `wlan0`. Mitigation: document that AP mode is the production access mode and keep SD-card recovery instructions for router-client access.
- AP country/channel constraints can block AP startup. Mitigation: set regulatory domain and use a conservative 2.4GHz channel.

## Migration Plan
1. Installer installs NetworkManager/AP dependencies.
2. Installer creates or updates the `vtx-hotspot` connection.
3. Installer enables NetworkManager and restarts it if needed.
4. Installer prints the AP SSID/password and URL.
5. Docs and validation checklists are updated.

## Rollback
Run `sudo nmcli connection delete vtx-hotspot` and restore normal Wi-Fi client settings through Raspberry Pi Imager, cloud-init recovery, or `raspi-config`.
