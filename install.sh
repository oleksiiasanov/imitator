#!/usr/bin/env bash
set -Eeuo pipefail

# VTX Player production installer for Raspberry Pi OS Lite.
# Safe to run more than once.

TOTAL_STEPS=9
STEP=0
REBOOT_REQUIRED=0
INSTALL_DONE=0
WIFI_AP_TOUCHED=0
WIFI_AP_EXISTED=0

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="vtx-player"
VENV="$INSTALL_DIR/.venv"
UNIT_TEMPLATE="$INSTALL_DIR/services/$SERVICE_NAME.service"
UNIT_DST="/etc/systemd/system/$SERVICE_NAME.service"
AP_CONNECTION="vtx-hotspot"
AP_INTERFACE="wlan0"
AP_SSID="VTX-SETUP"
AP_PASSWORD="vtxplayer"
AP_ADDRESS="10.42.0.1"
AP_PREFIX="24"
AP_CHANNEL="6"
BACKUP_DIR=""
OS_NAME="unknown"
OS_VERSION="unknown"
OS_CODENAME="unknown"

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[0;33m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

log() { printf '%s\n' "$*"; }
ok() { printf '%s✓ Done%s\n\n' "$GREEN" "$RESET"; }
info() { printf '  %s%s%s\n' "$YELLOW" "$*" "$RESET"; }
fail() { printf '\n%sERROR:%s %s\n' "$RED" "$RESET" "$*" >&2; exit 1; }

step() {
    STEP=$((STEP + 1))
    printf '%s[%s/%s]%s %s\n' "$BOLD" "$STEP" "$TOTAL_STEPS" "$RESET" "$1"
}

need_command() {
    command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"
}

detect_app_user() {
    if [ -n "${SUDO_USER:-}" ] && [ "$SUDO_USER" != "root" ] && id "$SUDO_USER" >/dev/null 2>&1; then
        printf '%s' "$SUDO_USER"
        return
    fi

    if id pi >/dev/null 2>&1; then
        printf '%s' "pi"
        return
    fi

    fail "Cannot find the Raspberry Pi user. Run with sudo from your normal user, or create a user named pi."
}

find_boot_files() {
    if [ -f /boot/firmware/config.txt ] && [ -f /boot/firmware/cmdline.txt ]; then
        BOOT_CONFIG="/boot/firmware/config.txt"
        BOOT_CMDLINE="/boot/firmware/cmdline.txt"
    elif [ -f /boot/config.txt ] && [ -f /boot/cmdline.txt ]; then
        BOOT_CONFIG="/boot/config.txt"
        BOOT_CMDLINE="/boot/cmdline.txt"
    else
        fail "Cannot find Raspberry Pi boot config files. Expected /boot/firmware/config.txt or /boot/config.txt."
    fi
}

detect_os() {
    if [ -r /etc/os-release ]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        OS_NAME="${PRETTY_NAME:-${NAME:-unknown}}"
        OS_VERSION="${VERSION_ID:-unknown}"
        OS_CODENAME="${VERSION_CODENAME:-unknown}"
    fi
}

backup_file() {
    local path="$1"
    local name
    name="$(printf '%s' "$path" | sed 's|/|_|g')"
    cp -a "$path" "$BACKUP_DIR/$name"
}

restore_file() {
    local path="$1"
    local name
    name="$(printf '%s' "$path" | sed 's|/|_|g')"
    if [ -f "$BACKUP_DIR/$name" ]; then
        cp -a "$BACKUP_DIR/$name" "$path"
    fi
}

rollback() {
    local exit_code=$?

    if [ "$INSTALL_DONE" -eq 1 ]; then
        exit "$exit_code"
    fi

    printf '\n%sInstallation failed.%s\n' "$RED" "$RESET" >&2

    if [ -n "$BACKUP_DIR" ] && [ -d "$BACKUP_DIR" ]; then
        info "Restoring files changed by this installer..."
        [ -n "${BOOT_CONFIG:-}" ] && restore_file "$BOOT_CONFIG"
        [ -n "${BOOT_CMDLINE:-}" ] && restore_file "$BOOT_CMDLINE"

        if [ -f "$BACKUP_DIR/unit" ]; then
            cp -a "$BACKUP_DIR/unit" "$UNIT_DST"
            systemctl daemon-reload >/dev/null 2>&1 || true
        elif [ -f "$UNIT_DST" ]; then
            rm -f "$UNIT_DST"
            systemctl daemon-reload >/dev/null 2>&1 || true
        fi

        if [ "$WIFI_AP_TOUCHED" -eq 1 ] && command -v nmcli >/dev/null 2>&1; then
            if [ "$WIFI_AP_EXISTED" -eq 1 ] && [ -f "$BACKUP_DIR/$AP_CONNECTION.nmconnection" ]; then
                info "Restoring Wi-Fi AP NetworkManager profile..."
                local ap_restore_path
                ap_restore_path="$(cat "$BACKUP_DIR/$AP_CONNECTION.path" 2>/dev/null || true)"
                if [ -n "$ap_restore_path" ]; then
                    cp -a "$BACKUP_DIR/$AP_CONNECTION.nmconnection" "$ap_restore_path"
                    chmod 600 "$ap_restore_path" || true
                fi
                nmcli connection reload >/dev/null 2>&1 || true
            elif nmcli connection show "$AP_CONNECTION" >/dev/null 2>&1; then
                info "Removing Wi-Fi AP profile created by this installer..."
                nmcli connection delete "$AP_CONNECTION" >/dev/null 2>&1 || true
            fi
        fi
    fi

    printf '%sCheck logs above, fix the reported error, then run sudo bash install.sh again.%s\n' "$YELLOW" "$RESET" >&2
    exit "$exit_code"
}

trap rollback ERR

set_config_value() {
    local key="$1"
    local value="$2"
    local line="$key=$value"

    if grep -qE "^[[:space:]]*#?[[:space:]]*$key=" "$BOOT_CONFIG"; then
        if ! grep -qE "^[[:space:]]*$key=$value[[:space:]]*$" "$BOOT_CONFIG"; then
            sed -i -E "s|^[[:space:]]*#?[[:space:]]*$key=.*|$line|" "$BOOT_CONFIG"
            REBOOT_REQUIRED=1
        fi
    else
        printf '%s\n' "$line" >> "$BOOT_CONFIG"
        REBOOT_REQUIRED=1
    fi
}

set_config_line() {
    local pattern="$1"
    local line="$2"

    if grep -qE "$pattern" "$BOOT_CONFIG"; then
        if ! grep -qF "$line" "$BOOT_CONFIG"; then
            sed -i -E "s|$pattern.*|$line|" "$BOOT_CONFIG"
            REBOOT_REQUIRED=1
        fi
    else
        printf '%s\n' "$line" >> "$BOOT_CONFIG"
        REBOOT_REQUIRED=1
    fi
}

add_cmdline_token() {
    local token="$1"
    if ! grep -Fq "$token" "$BOOT_CMDLINE"; then
        sed -i "s/$/ $token/" "$BOOT_CMDLINE"
        REBOOT_REQUIRED=1
    fi
}

set_composite_cmdline() {
    local token="video=Composite-1:720x576@50e"

    if grep -qE '(^| )video=Composite-1:[^ ]+' "$BOOT_CMDLINE"; then
        if ! grep -Fq "$token" "$BOOT_CMDLINE"; then
            sed -i -E "s|(^| )video=Composite-1:[^ ]+| $token|" "$BOOT_CMDLINE"
            REBOOT_REQUIRED=1
        fi
    else
        sed -i "s/$/ $token/" "$BOOT_CMDLINE"
        REBOOT_REQUIRED=1
    fi
}

disable_graphical_desktop() {
    local display_services=(
        display-manager.service
        lightdm.service
        gdm.service
        gdm3.service
        sddm.service
        wayfire.service
        labwc.service
    )

    if [ "$(systemctl get-default 2>/dev/null || true)" != "multi-user.target" ]; then
        systemctl set-default multi-user.target
        REBOOT_REQUIRED=1
    fi

    for service in "${display_services[@]}"; do
        if systemctl list-unit-files "$service" >/dev/null 2>&1; then
            systemctl disable "$service" >/dev/null 2>&1 || true
            systemctl stop "$service" --no-block >/dev/null 2>&1 || true
        fi
    done

    pkill -TERM -f 'labwc|wayfire|weston|Xorg|pcmanfm|wf-panel-pi|kanshi|lwrespawn' >/dev/null 2>&1 || true
    sleep 1
    pkill -KILL -f 'labwc|wayfire|weston|Xorg|pcmanfm|wf-panel-pi|kanshi|lwrespawn' >/dev/null 2>&1 || true
}

stop_existing_service() {
    if systemctl list-unit-files "$SERVICE_NAME.service" >/dev/null 2>&1; then
        if systemctl is-active --quiet "$SERVICE_NAME.service"; then
            info "Stopping existing $SERVICE_NAME service before self-check..."
            systemctl stop "$SERVICE_NAME.service"
            sleep 1
        fi
    fi
}

configure_wifi_ap() {
    need_command nmcli

    systemctl enable NetworkManager >/dev/null 2>&1 || true
    systemctl start NetworkManager >/dev/null 2>&1 || true
    nmcli radio wifi on >/dev/null 2>&1 || true

    if nmcli connection show "$AP_CONNECTION" >/dev/null 2>&1; then
        WIFI_AP_EXISTED=1
        local filename
        filename="$(nmcli -g connection.filename connection show "$AP_CONNECTION" 2>/dev/null || true)"
        if [ -n "$filename" ] && [ -f "$filename" ]; then
            cp -a "$filename" "$BACKUP_DIR/$AP_CONNECTION.nmconnection"
            printf '%s\n' "$filename" > "$BACKUP_DIR/$AP_CONNECTION.path"
        fi
    else
        nmcli connection add \
            type wifi \
            ifname "$AP_INTERFACE" \
            con-name "$AP_CONNECTION" \
            autoconnect yes \
            ssid "$AP_SSID" >/dev/null
        REBOOT_REQUIRED=1
    fi

    WIFI_AP_TOUCHED=1

    nmcli connection modify "$AP_CONNECTION" \
        connection.autoconnect yes \
        connection.autoconnect-priority 100 \
        connection.interface-name "$AP_INTERFACE" \
        802-11-wireless.mode ap \
        802-11-wireless.ssid "$AP_SSID" \
        802-11-wireless.band bg \
        802-11-wireless.channel "$AP_CHANNEL" \
        wifi-sec.key-mgmt wpa-psk \
        wifi-sec.psk "$AP_PASSWORD" \
        ipv4.method shared \
        ipv4.addresses "$AP_ADDRESS/$AP_PREFIX" \
        ipv6.method disabled

    nmcli connection reload >/dev/null
}

panel_url() {
    printf 'http://%s:8080\n' "$AP_ADDRESS"
}

if [ "$(id -u)" -ne 0 ]; then
    fail "Run as root: sudo bash install.sh"
fi

step "Checking system and project files..."
need_command apt-get
need_command sed
need_command grep
need_command awk
need_command systemctl
detect_os
find_boot_files
APP_USER="$(detect_app_user)"
[ -f "$INSTALL_DIR/app.py" ] || fail "Missing app.py in $INSTALL_DIR"
[ -f "$INSTALL_DIR/requirements.txt" ] || fail "Missing requirements.txt in $INSTALL_DIR"
[ -f "$UNIT_TEMPLATE" ] || fail "Missing systemd template: $UNIT_TEMPLATE"
BACKUP_DIR="$(mktemp -d)"
backup_file "$BOOT_CONFIG"
backup_file "$BOOT_CMDLINE"
if [ -f "$UNIT_DST" ]; then
    cp -a "$UNIT_DST" "$BACKUP_DIR/unit"
fi
stop_existing_service
info "Install directory: $INSTALL_DIR"
info "Application user: $APP_USER"
info "Detected OS: $OS_NAME"
info "Boot config: $BOOT_CONFIG"
ok

step "Installing packages..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    ffmpeg mpv procps network-manager \
    gpiod python3-gpiozero python3-lgpio

need_command ffmpeg
need_command mpv
need_command nmcli
ok

step "Configuring Wi-Fi Access Point..."
configure_wifi_ap
ok

step "Configuring Composite..."
set_config_value "enable_tvout" "1"
set_config_value "sdtv_mode" "2"
set_config_value "disable_overscan" "1"
set_config_value "hdmi_ignore_hotplug" "1"
set_config_line "^[[:space:]]*#?[[:space:]]*dtoverlay=vc4-kms-v3d" "dtoverlay=vc4-kms-v3d,composite=1"
set_composite_cmdline
add_cmdline_token "quiet"
add_cmdline_token "loglevel=3"
add_cmdline_token "logo.nologo"
add_cmdline_token "vt.global_cursor_default=0"
disable_graphical_desktop
ok

step "Installing Python dependencies..."
if [ ! -d "$VENV" ]; then
    python3 -m venv --system-site-packages "$VENV"
elif [ -f "$VENV/pyvenv.cfg" ]; then
    if grep -q "^include-system-site-packages = " "$VENV/pyvenv.cfg"; then
        sed -i -E "s/^include-system-site-packages = .*/include-system-site-packages = true/" "$VENV/pyvenv.cfg"
    else
        printf '%s\n' "include-system-site-packages = true" >> "$VENV/pyvenv.cfg"
    fi
fi
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install --no-warn-conflicts -r "$INSTALL_DIR/requirements.txt"
"$VENV/bin/python" - << PY
from importlib.metadata import PackageNotFoundError, version
import gpiozero
import lgpio


def installed_version(package_name):
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "apt"


print("Flask", version("flask"))
print("Werkzeug", version("werkzeug"))
print("gpiozero", installed_version("gpiozero"))
print("lgpio", installed_version("lgpio"))
PY
ok

step "Creating runtime directories..."
mkdir -p "$INSTALL_DIR/uploads" "$INSTALL_DIR/videos"
touch "$INSTALL_DIR/config.json"
chown -R "$APP_USER:$APP_USER" "$INSTALL_DIR/uploads" "$INSTALL_DIR/videos"
chown "$APP_USER:$APP_USER" "$INSTALL_DIR/config.json"
chmod 755 "$INSTALL_DIR" "$INSTALL_DIR/uploads" "$INSTALL_DIR/videos"
ok

step "Installing systemd service..."
sed \
    -e "s|/home/pi/imitator|$INSTALL_DIR|g" \
    -e "s|^User=.*|User=$APP_USER|g" \
    "$UNIT_TEMPLATE" > "$UNIT_DST"
chmod 644 "$UNIT_DST"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
ok

step "Running application self-check..."
"$VENV/bin/python" - << PY
import sys
sys.path.insert(0, "$INSTALL_DIR")
import app

diagnostics = app.collect_diagnostics()
for check in diagnostics["checks"]:
    marker = "OK" if check["ok"] else "FAIL"
    print(f"{marker}: {check['label']} - {check['message']}")

required_before_reboot = {"ffmpeg", "mpv", "GPIO17", "Wi-Fi AP", "uploads", "videos", "config.json"}
failed = [
    check["label"]
    for check in diagnostics["checks"]
    if not check["ok"] and check["label"] in required_before_reboot
]

if failed:
    raise SystemExit("Self-check failed before reboot: " + ", ".join(failed))
PY
chown "$APP_USER:$APP_USER" "$INSTALL_DIR/config.json"
ok

step "Starting service..."
if [ "$REBOOT_REQUIRED" -eq 1 ]; then
    info "A reboot is required for Raspberry Pi composite output."
else
    systemctl restart "$SERVICE_NAME"
    sleep 2
    systemctl is-active --quiet "$SERVICE_NAME" || {
        journalctl -u "$SERVICE_NAME" -n 80 --no-pager
        fail "Service did not start. See the journal output above."
    }
fi
ok

INSTALL_DONE=1
trap - ERR

log "${GREEN}Installation completed.${RESET}"
log ""
log "Open:"
log ""
log "$(panel_url)"
log ""
log "Wi-Fi:"
log "SSID: $AP_SSID"
log "Password: $AP_PASSWORD"
log ""
log "System:"
log "$OS_NAME (version: $OS_VERSION, codename: $OS_CODENAME)"
log ""
log "Python:"
log "$VENV/bin/python"
log ""
log "Logs:"
log "journalctl -u $SERVICE_NAME -f"

if [ "$REBOOT_REQUIRED" -eq 1 ]; then
    log ""
    info "Rebooting in 10 seconds. After reboot, the web panel starts automatically."
    sleep 10
    reboot
fi
