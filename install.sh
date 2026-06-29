#!/usr/bin/env bash
set -Eeuo pipefail

# VTX Player production installer for Raspberry Pi OS Lite.
# Safe to run more than once.

TOTAL_STEPS=8
STEP=0
REBOOT_REQUIRED=0
INSTALL_DONE=0

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="vtx-player"
VENV="$INSTALL_DIR/.venv"
UNIT_TEMPLATE="$INSTALL_DIR/services/$SERVICE_NAME.service"
UNIT_DST="/etc/systemd/system/$SERVICE_NAME.service"
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

panel_url() {
    local ip_addr=""

    if command -v hostname >/dev/null 2>&1; then
        ip_addr="$(hostname -I 2>/dev/null | awk '{print $1}')"
    fi

    if [ -n "$ip_addr" ]; then
        printf 'http://%s:8080\n' "$ip_addr"
    else
        printf '%s\n' "http://<raspberry-pi-ip>:8080"
    fi
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
info "Install directory: $INSTALL_DIR"
info "Application user: $APP_USER"
info "Detected OS: $OS_NAME"
info "Boot config: $BOOT_CONFIG"
ok

step "Installing packages..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    ffmpeg mpv procps \
    gpiod python3-gpiozero python3-lgpio

need_command ffmpeg
need_command mpv
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
"$VENV/bin/python" -m pip install -r "$INSTALL_DIR/requirements.txt"
"$VENV/bin/python" - << PY
from importlib.metadata import version
import gpiozero
import lgpio
print("Flask", version("flask"))
print("Werkzeug", version("werkzeug"))
print("gpiozero", gpiozero.__version__)
print("lgpio", getattr(lgpio, "__version__", "apt"))
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

required_before_reboot = {"ffmpeg", "mpv", "GPIO17", "uploads", "videos", "config.json"}
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
