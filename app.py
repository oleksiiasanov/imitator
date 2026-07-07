import atexit
import json
import logging
import os
import signal
import shutil
import subprocess
import sys
import threading
import time
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path

from flask import Flask, request, redirect, render_template, jsonify
from werkzeug.utils import secure_filename

import gpio


APP_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = APP_DIR / "uploads"
VIDEO_DIR = APP_DIR / "videos"
CONFIG_PATH = APP_DIR / "config.json"
VERSION_PATH = APP_DIR / "VERSION"

FPV_VIDEO = VIDEO_DIR / "video_fpv.mp4"
APP_STARTED_AT = time.time()
MOSFET_SETTLE_SECONDS = 0.3
AP_CONNECTION = "vtx-hotspot"
AP_INTERFACE = "wlan0"
AP_SSID = "VTX-SETUP"
AP_ADDRESS = "10.42.0.1"

APP_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024 * 1024  # 4GB
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [vtx-player] %(message)s",
)

scheduler_generation = 0
scheduler_lock = threading.Lock()
player_lock = threading.RLock()
config_lock = threading.RLock()
upload_lock = threading.Lock()
conversion_lock = threading.Lock()
conversion_state_lock = threading.Lock()
runtime_error_lock = threading.Lock()
player_process = None
shutdown_handlers_registered = False

conversion_state = {
    "running": False,
    "phase": "idle",
    "percent": 0,
    "ok": False,
    "error": "",
    "message": "Готово до завантаження відео",
    "filename": "",
    "updated_at": APP_STARTED_AT,
}

runtime_error = ""


DEFAULT_CONFIG = {
    "autoplay_enabled": False,
    "start_delay_seconds": 0,
    "interval_seconds": 1200
}

ALLOWED_VIDEO_EXTENSIONS = {
    ".avi",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".ts",
    ".webm",
}


def load_app_version():
    try:
        version = VERSION_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"

    return version or "unknown"


def update_conversion_state(**updates):
    with conversion_state_lock:
        conversion_state.update(updates)
        conversion_state["updated_at"] = time.time()


def conversion_status():
    with conversion_state_lock:
        state = conversion_state.copy()

    state["updated_ago"] = format_duration(time.time() - state["updated_at"])
    return state


def conversion_running():
    with conversion_state_lock:
        return bool(conversion_state["running"])


def set_runtime_error(message):
    global runtime_error

    with runtime_error_lock:
        runtime_error = message


def clear_runtime_error():
    set_runtime_error("")


def get_runtime_error():
    with runtime_error_lock:
        return runtime_error


def validate_video_file(file):
    filename = secure_filename(file.filename or "")
    if not filename:
        return False, "", "No file selected"

    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_VIDEO_EXTENSIONS))
        return False, "", f"Unsupported video file type: {extension or 'no extension'}. Allowed: {allowed}"

    return True, filename, ""


def status_item(ok, label, value, detail=""):
    return {
        "ok": ok,
        "label": label,
        "value": value,
        "detail": detail,
    }


def format_bytes(size):
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024


def format_duration(seconds):
    seconds = max(0, int(seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or parts:
        parts.append(f"{hours}h")
    if minutes or parts:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def installed_package_version(package_name):
    try:
        return package_version(package_name)
    except PackageNotFoundError:
        return "not installed"


def readonly_command_status(command):
    path = shutil.which(command)
    if path:
        return status_item(True, command.upper(), "Available", path)

    return status_item(False, command.upper(), "Missing", f"Install package: {command}")


def run_readonly_command(args, timeout=3):
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        app.logger.debug("Read-only command failed: %s: %s", args, exc)
        return None


def nmcli_connection_value(field):
    if not shutil.which("nmcli"):
        return ""

    result = run_readonly_command(["nmcli", "-g", field, "connection", "show", AP_CONNECTION])
    if not result or result.returncode != 0:
        return ""

    return result.stdout.strip()


def active_ap_connection():
    if not shutil.which("nmcli"):
        return False, ""

    result = run_readonly_command(["nmcli", "-t", "-f", "NAME,DEVICE", "connection", "show", "--active"])
    if not result or result.returncode != 0:
        return False, ""

    for line in result.stdout.splitlines():
        name, _, device = line.partition(":")
        if name == AP_CONNECTION:
            return True, device or AP_INTERFACE

    return False, ""


def readonly_wifi_ap_status():
    if not shutil.which("nmcli"):
        return status_item(False, "Wi-Fi AP", "Missing", "NetworkManager nmcli command is not installed.")

    result = run_readonly_command(["nmcli", "connection", "show", AP_CONNECTION])
    if not result:
        return status_item(False, "Wi-Fi AP", "Unknown", "Unable to run nmcli.")

    if result.returncode != 0:
        detail = result.stderr.strip() or f"Connection {AP_CONNECTION} was not found."
        return status_item(False, "Wi-Fi AP", "Not configured", detail)

    ssid = nmcli_connection_value("802-11-wireless.ssid") or "unknown"
    mode = nmcli_connection_value("802-11-wireless.mode") or "unknown"
    method = nmcli_connection_value("ipv4.method") or "unknown"
    addresses = nmcli_connection_value("ipv4.addresses") or "unknown"
    active, device = active_ap_connection()

    value = "Active" if active else "Configured"
    detail = (
        f"SSID: {ssid}; connection: {AP_CONNECTION}; interface: {device or AP_INTERFACE}; "
        f"mode: {mode}; IPv4: {method} {addresses}; URL: http://{AP_ADDRESS}:8080"
    )

    expected = ssid == AP_SSID and mode == "ap" and method == "shared" and AP_ADDRESS in addresses
    return status_item(expected, "Wi-Fi AP", value if expected else "Misconfigured", detail)


def readonly_composite_status():
    status_files = sorted(Path("/sys/class/drm").glob("card*-Composite-1/status"))

    if not status_files:
        return status_item(False, "Composite enabled", "Not detected", "Composite-1 status file was not found.")

    statuses = []
    for status_file in status_files:
        try:
            status = status_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            statuses.append(f"{status_file}: unreadable ({exc})")
            continue

        statuses.append(f"{status_file}: {status}")
        if status == "connected":
            return status_item(True, "Composite enabled", "Connected", str(status_file))

    return status_item(False, "Composite enabled", "Not connected", "; ".join(statuses))


def readonly_current_video_status():
    if not FPV_VIDEO.exists():
        return status_item(False, "Current video", "Missing", str(FPV_VIDEO))

    try:
        stat = FPV_VIDEO.stat()
    except OSError as exc:
        return status_item(False, "Current video", "Unreadable", str(exc))

    modified = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))
    return status_item(True, "Current video", format_bytes(stat.st_size), f"{FPV_VIDEO} · modified {modified}")


def readonly_free_disk_status():
    try:
        usage = shutil.disk_usage(APP_DIR)
    except OSError as exc:
        return status_item(False, "Free space", "Unknown", str(exc))

    detail = f"{format_bytes(usage.free)} free of {format_bytes(usage.total)} total"
    return status_item(True, "Free space", format_bytes(usage.free), detail)


def readonly_gpio_status():
    state = gpio.status()
    if not state["ok"]:
        return status_item(False, "GPIO17", "Unavailable", state["error"])

    value = "ON" if state["powered"] else "OFF"
    detail = f"Backend: {state['backend']}; pin: GPIO{state['pin']}"
    return status_item(True, "GPIO17", value, detail)


def readonly_mosfet_status():
    state = gpio.status()
    if not state["ok"]:
        return status_item(False, "Power switching", "Unavailable", state["error"])

    value = "Enabled" if state["powered"] else "Ready"
    detail = "GPIO17 controls the MOSFET gate and is turned off on stop or application exit."
    return status_item(True, "Power switching", value, detail)


def collect_system_status():
    return [
        {
            "title": "Application",
            "items": [
                status_item(True, "Version", load_app_version(), str(VERSION_PATH)),
                status_item(True, "Python", sys.version.split()[0], sys.executable),
                status_item(True, "Flask", installed_package_version("flask")),
            ],
        },
        {
            "title": "Playback",
            "items": [
                readonly_command_status("mpv"),
                readonly_command_status("ffmpeg"),
                readonly_current_video_status(),
            ],
        },
        {
            "title": "Video",
            "items": [
                readonly_composite_status(),
            ],
        },
        {
            "title": "Wi-Fi",
            "items": [
                readonly_wifi_ap_status(),
            ],
        },
        {
            "title": "Storage",
            "items": [
                readonly_free_disk_status(),
            ],
        },
        {
            "title": "Runtime",
            "items": [
                status_item(True, "Uptime", format_duration(time.time() - APP_STARTED_AT)),
            ],
        },
        {
            "title": "GPIO",
            "items": [
                readonly_gpio_status(),
            ],
        },
        {
            "title": "MOSFET",
            "items": [
                readonly_mosfet_status(),
            ],
        },
    ]


def diagnostic(ok, label, message):
    return {
        "ok": ok,
        "label": label,
        "message": message,
    }


def command_check(command, package_name):
    path = shutil.which(command)
    if path:
        return diagnostic(True, command, f"Знайдено: {path}")

    return diagnostic(
        False,
        command,
        f"Не знайдено команду {command}. Запусти: sudo bash install.sh або встанови пакет {package_name}."
    )


def wifi_ap_check():
    status = readonly_wifi_ap_status()
    if status["ok"]:
        return diagnostic(True, "Wi-Fi AP", status["detail"])

    return diagnostic(
        False,
        "Wi-Fi AP",
        f"{status['value']}: {status['detail']}. Запусти sudo bash install.sh і перезавантаж Raspberry Pi."
    )


def directory_check(path, label):
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return diagnostic(False, label, f"Не можу створити папку {path}: {exc}")

    if not path.is_dir():
        return diagnostic(False, label, f"{path} існує, але це не папка.")

    if not os.access(path, os.R_OK | os.W_OK | os.X_OK):
        return diagnostic(False, label, f"Немає прав читання/запису для {path}.")

    return diagnostic(True, label, f"Папка доступна: {path}")


def config_check():
    try:
        config = load_config()
        save_config(config)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        return diagnostic(False, "config.json", f"Не можу прочитати або записати {CONFIG_PATH}: {exc}")

    return diagnostic(True, "config.json", f"Конфіг доступний: {CONFIG_PATH}")


def composite_check():
    status_files = sorted(Path("/sys/class/drm").glob("card*-Composite-1/status"))

    if not status_files:
        return diagnostic(
            False,
            "Composite-1",
            "Composite-1 не знайдено в /sys/class/drm. Перевір install.sh і перезавантаж Raspberry Pi."
        )

    for status_file in status_files:
        try:
            status = status_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            return diagnostic(False, "Composite-1", f"Не можу прочитати {status_file}: {exc}")

        if status == "connected":
            return diagnostic(True, "Composite-1", f"{status_file}: connected")

    statuses = []
    for status_file in status_files:
        try:
            statuses.append(f"{status_file.name}={status_file.read_text(encoding='utf-8').strip()}")
        except OSError as exc:
            statuses.append(f"{status_file.name}=unreadable ({exc})")

    return diagnostic(
        False,
        "Composite-1",
        f"Composite-1 знайдено, але він не connected: {', '.join(statuses)}. Перевір проводку/VTX/receiver."
    )


def gpio_check():
    state = gpio.status()
    if state["ok"]:
        power_state = "ON" if state["powered"] else "OFF"
        return diagnostic(
            True,
            "GPIO17",
            f"GPIO17 доступний через {state['backend']}. MOSFET зараз {power_state}."
        )

    return diagnostic(
        False,
        "GPIO17",
        "GPIO17 недоступний для MOSFET: "
        f"{state['error']}. Запусти sudo bash install.sh і перевір, що це Raspberry Pi."
    )


def collect_diagnostics():
    checks = [
        command_check("ffmpeg", "ffmpeg"),
        command_check("mpv", "mpv"),
        wifi_ap_check(),
        composite_check(),
        gpio_check(),
        directory_check(UPLOAD_DIR, "uploads"),
        directory_check(VIDEO_DIR, "videos"),
        config_check(),
    ]

    return {
        "checks": checks,
        "ok": all(check["ok"] for check in checks),
    }


def normalize_config(data):
    config = DEFAULT_CONFIG.copy()

    if isinstance(data, dict):
        config.update(data)

    config["autoplay_enabled"] = bool(config.get("autoplay_enabled"))

    try:
        config["start_delay_seconds"] = max(0, int(config.get("start_delay_seconds", 0)))
    except (TypeError, ValueError):
        config["start_delay_seconds"] = DEFAULT_CONFIG["start_delay_seconds"]

    try:
        config["interval_seconds"] = max(60, int(config.get("interval_seconds", 1200)))
    except (TypeError, ValueError):
        config["interval_seconds"] = DEFAULT_CONFIG["interval_seconds"]

    return config


def load_config():
    with config_lock:
        if not CONFIG_PATH.exists():
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()

        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                return normalize_config(json.load(f))
        except (OSError, json.JSONDecodeError):
            return DEFAULT_CONFIG.copy()


def save_config(config):
    config = normalize_config(config)
    temp_path = CONFIG_PATH.with_suffix(".json.tmp")

    with config_lock:
        temp_path.write_text(
            json.dumps(config, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )
        os.replace(temp_path, CONFIG_PATH)


def run(cmd):
    try:
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except OSError as exc:
        return subprocess.CompletedProcess(cmd, 127, "", str(exc))


def safe_power_on():
    try:
        gpio.power_on()
        app.logger.info("GPIO17 MOSFET power enabled")
        time.sleep(MOSFET_SETTLE_SECONDS)
        return True, ""
    except gpio.GPIOError as exc:
        safe_power_off("failed power-on")
        app.logger.error("GPIO17 MOSFET power-on failed: %s", exc)
        return False, f"GPIO17/MOSFET недоступний: {exc}"
    except (gpio.GPIOError, RuntimeError, OSError) as exc:
        safe_power_off("failed power-on")
        app.logger.exception("Unexpected GPIO17 MOSFET power-on error")
        return False, f"Помилка GPIO17/MOSFET: {exc}"


def safe_power_off(reason=""):
    try:
        gpio.power_off()
        if reason:
            app.logger.info("GPIO17 MOSFET power disabled: %s", reason)
        else:
            app.logger.info("GPIO17 MOSFET power disabled")
    except (gpio.GPIOError, RuntimeError, OSError):
        app.logger.exception("Failed to disable GPIO17 MOSFET power")


def watch_player_process(proc, label):
    def _watch():
        try:
            returncode = proc.wait()
        except (subprocess.SubprocessError, OSError, RuntimeError):
            app.logger.exception("%s watcher failed", label)
            returncode = None

        should_power_off = False
        with player_lock:
            global player_process
            if player_process is proc:
                player_process = None
                should_power_off = True

        if should_power_off:
            app.logger.info("%s exited with return code %s", label, returncode)
            safe_power_off(f"{label} exited")

    thread = threading.Thread(target=_watch, daemon=True)
    thread.start()


def video_duration_seconds(input_path):
    result = run([
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(input_path),
    ])

    if result.returncode != 0:
        app.logger.warning("ffprobe duration check failed: %s", result.stderr.strip())
        return None

    try:
        duration = float(result.stdout.strip())
    except ValueError:
        return None

    if duration <= 0:
        return None

    return duration


def player_running():
    with player_lock:
        if player_process is not None and player_process.poll() is None:
            return True

    result = run(["pgrep", "-f", "mpv.*Composite-1"])
    return result.returncode == 0


def stop_player():
    global player_process

    proc = None
    with player_lock:
        if player_process is not None:
            proc = player_process
            player_process = None

        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                app.logger.warning("MPV did not stop after SIGTERM; killing it")
                proc.kill()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    app.logger.error("MPV did not exit after SIGKILL; continuing shutdown")

        result = run(["pkill", "-f", "mpv.*Composite-1"])
        if result.returncode not in (0, 1):
            app.logger.warning("Failed to stop mpv: %s", result.stderr.strip())

    safe_power_off("playback stopped")


def mpv_base_cmd():
    return [
        "mpv",
        "--vo=drm",
        "--drm-device=/dev/dri/card0",
        "--drm-connector=Composite-1",
        "--fs",
        "--msg-level=all=warn",
        "--term-osd=no",
    ]


def start_player_loop(allow_while_converting=False):
    global player_process

    if conversion_running() and not allow_while_converting:
        return False, "Конвертація ще триває. Дочекайся завершення."

    if not FPV_VIDEO.exists():
        app.logger.warning("Cannot start playback: %s does not exist", FPV_VIDEO)
        return False, "Відео ще не завантажене"

    with player_lock:
        if player_running():
            return True, "Відео вже запущене"

        cmd = mpv_base_cmd() + [
            "--loop=inf",
            str(FPV_VIDEO)
        ]

        powered, power_error = safe_power_on()
        if not powered:
            return False, power_error

        try:
            proc = subprocess.Popen(
                cmd,
                start_new_session=True,
            )
        except OSError as exc:
            safe_power_off("mpv loop start failed")
            app.logger.exception("Failed to start mpv loop")
            return False, f"MPV не запустився: {exc}"

        player_process = proc
        watch_player_process(proc, "MPV loop")

    app.logger.info("Started MPV loop for %s", FPV_VIDEO)
    return True, "Відео запущене"


def play_video_once():
    global player_process

    if not FPV_VIDEO.exists():
        app.logger.warning("Scheduler skipped playback: %s does not exist", FPV_VIDEO)
        return False

    stop_player()

    cmd = mpv_base_cmd() + [
        str(FPV_VIDEO)
    ]

    try:
        with player_lock:
            powered, power_error = safe_power_on()
            if not powered:
                app.logger.error("Scheduler skipped playback: %s", power_error)
                return False

            proc = subprocess.Popen(
                cmd,
                start_new_session=True,
            )
            player_process = proc
        proc.wait()
    except OSError:
        app.logger.exception("Failed to play video once")
        return False
    finally:
        with player_lock:
            if "proc" in locals() and player_process is proc:
                player_process = None
        safe_power_off("scheduled playback finished")

    return True


def convert_video(input_path, progress_callback=None):
    stop_player()

    temp_output = FPV_VIDEO.with_suffix(".tmp.mp4")
    duration = video_duration_seconds(input_path)

    cmd = [
        "ffmpeg",
        "-y",
        "-progress", "pipe:1",
        "-nostats",
        "-i", str(input_path),
        "-vf", "scale=640:480,fps=30",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-b:v", "1500k",
        "-an",
        str(temp_output),
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        temp_output.unlink(missing_ok=True)
        return False, str(exc)

    if proc.stdout:
        for line in proc.stdout:
            line = line.strip()
            if not line or "=" not in line:
                continue

            key, value = line.split("=", 1)
            if key == "out_time_ms" and duration and progress_callback:
                try:
                    current = int(value) / 1_000_000
                except ValueError:
                    continue

                percent = max(1, min(99, int((current / duration) * 100)))
                progress_callback(percent)
            elif key == "progress" and value == "end" and progress_callback:
                progress_callback(100)

    stderr = proc.stderr.read() if proc.stderr else ""
    returncode = proc.wait()

    if returncode != 0:
        temp_output.unlink(missing_ok=True)
        app.logger.error("FFmpeg conversion failed: %s", stderr.strip())
        return False, stderr

    os.replace(temp_output, FPV_VIDEO)
    app.logger.info("Converted video to %s", FPV_VIDEO)
    return True, "OK"


def convert_video_job(input_path, filename):
    with conversion_lock:
        update_conversion_state(
            running=True,
            phase="converting",
            percent=0,
            ok=False,
            error="",
            message="Конвертація почалась",
            filename=filename,
        )

        def progress(percent):
            update_conversion_state(
                phase="converting",
                percent=percent,
                message=f"Конвертація: {percent}%",
            )

        ok, result = convert_video(input_path, progress)

        if not ok:
            set_runtime_error("Помилка конвертації відео. Деталі є у повідомленні upload status і journal.")
            update_conversion_state(
                running=False,
                phase="error",
                percent=0,
                ok=False,
                error=result[-3000:],
                message="Помилка конвертації",
            )
            return

        update_conversion_state(
            running=True,
            phase="starting",
            percent=100,
            ok=True,
            error="",
            message="Конвертація завершена. Запускаю відтворення...",
        )

        playback_ok, playback_message = start_player_loop(allow_while_converting=True)
        if not playback_ok:
            set_runtime_error(playback_message)
            update_conversion_state(
                running=False,
                phase="error",
                percent=100,
                ok=False,
                error=playback_message,
                message="Відео конвертовано, але MPV не запустився",
            )
            return

        update_conversion_state(
            running=False,
            phase="complete",
            percent=100,
            ok=True,
            error="",
            message="Готово. Відео завантажено, конвертовано і запущено.",
        )
        clear_runtime_error()


def restart_scheduler():
    global scheduler_generation

    with scheduler_lock:
        scheduler_generation += 1
        current_generation = scheduler_generation

    thread = threading.Thread(
        target=scheduler_loop,
        args=(current_generation,),
        daemon=True
    )
    thread.start()
    app.logger.info("Scheduler restarted: generation=%s", current_generation)


def scheduler_loop(my_generation):
    config = load_config()

    if not config.get("autoplay_enabled"):
        return

    start_delay = config["start_delay_seconds"]

    waited = 0
    while waited < start_delay:
        with scheduler_lock:
            if my_generation != scheduler_generation:
                return

        time.sleep(1)
        waited += 1

    while True:
        with scheduler_lock:
            if my_generation != scheduler_generation:
                return

        config = load_config()
        if not config.get("autoplay_enabled"):
            return

        play_video_once()

        interval = config["interval_seconds"]
        waited = 0

        while waited < interval:
            with scheduler_lock:
                if my_generation != scheduler_generation:
                    return

            time.sleep(1)
            waited += 1


@app.route("/")
def index():
    config = load_config()
    diagnostics = collect_diagnostics()

    is_running = player_running()
    player_status = "запущене" if is_running else "зупинене"
    video_status = "video_fpv.mp4 є" if FPV_VIDEO.exists() else "відео ще не завантажене"
    toggle_label = "Пауза" if is_running else "Пуск"

    autoplay_status = "увімкнений" if config.get("autoplay_enabled") else "вимкнений"

    delay = int(config.get("start_delay_seconds", 0))
    interval = int(config.get("interval_seconds", 1200))

    delay_minutes = delay // 60
    interval_minutes = max(1, interval // 60)

    return render_template(
        "index.html",
        player_status=player_status,
        video_status=video_status,
        toggle_label=toggle_label,
        autoplay_status=autoplay_status,
        config=config,
        delay_minutes=delay_minutes,
        interval_minutes=interval_minutes,
        diagnostics=diagnostics,
        app_version=load_app_version(),
        conversion=conversion_status(),
        runtime_error=get_runtime_error(),
    )


@app.route("/system")
def system_page():
    return render_template(
        "system.html",
        sections=collect_system_status(),
    )


@app.route("/upload", methods=["POST"])
def upload():
    try:
        if conversion_running():
            return jsonify(ok=False, error="Conversion is already running. Please wait."), 409

        diagnostics = collect_diagnostics()
        if not diagnostics["ok"]:
            failed = [check["label"] for check in diagnostics["checks"] if not check["ok"]]
            message = "Self-check failed: " + ", ".join(failed)
            set_runtime_error(message)
            return jsonify(ok=False, error=message), 503

        with upload_lock:
            if "video" not in request.files:
                return jsonify(ok=False, error="No file field named video"), 400

            file = request.files["video"]
            valid, filename, error = validate_video_file(file)
            if not valid:
                return jsonify(ok=False, error=error), 400

            input_path = UPLOAD_DIR / filename
            app.logger.info("Received upload: %s", filename)

            for old_file in UPLOAD_DIR.glob("*"):
                if old_file.is_file():
                    old_file.unlink()

            file.save(input_path)

            if not input_path.exists() or input_path.stat().st_size == 0:
                return jsonify(ok=False, error="Uploaded file is empty"), 400

            update_conversion_state(
                running=True,
                phase="queued",
                percent=0,
                ok=False,
                error="",
                message="Файл завантажено. Очікую старт конвертації...",
                filename=filename,
            )

            thread = threading.Thread(
                target=convert_video_job,
                args=(input_path, filename),
                daemon=True,
            )
            thread.start()

        clear_runtime_error()
        return jsonify(ok=True, message="Upload complete. Conversion started.")

    except (OSError, RuntimeError, ValueError) as exc:
        message = f"Не вдалося завантажити відео: {exc}"
        set_runtime_error(message)
        app.logger.exception("Upload failed")
        return jsonify(ok=False, error=message), 500


@app.route("/upload-status")
def upload_status():
    return jsonify(conversion_status())


@app.route("/toggle", methods=["POST"])
def toggle():
    if conversion_running():
        app.logger.warning("Toggle blocked while conversion is running")
        set_runtime_error("Конвертація ще триває. Дочекайся завершення перед запуском відтворення.")
        return redirect("/")

    diagnostics = collect_diagnostics()
    if not diagnostics["ok"]:
        failed = [check["label"] for check in diagnostics["checks"] if not check["ok"]]
        message = "Playback blocked by self-check: " + ", ".join(failed)
        set_runtime_error(message)
        app.logger.error(message)
        return redirect("/")

    if player_running():
        stop_player()
        clear_runtime_error()
    else:
        ok, message = start_player_loop()
        if not ok:
            set_runtime_error(message)
            app.logger.error("Toggle start failed: %s", message)
        else:
            clear_runtime_error()

    return redirect("/")


@app.route("/settings", methods=["POST"])
def settings():
    autoplay_enabled = request.form.get("autoplay_enabled") == "on"

    try:
        delay_minutes = int(request.form.get("delay_minutes", 0))
    except (TypeError, ValueError):
        delay_minutes = 0

    try:
        interval_minutes = int(request.form.get("interval_minutes", 20))
    except (TypeError, ValueError):
        interval_minutes = 20

    delay_minutes = max(0, delay_minutes)
    interval_minutes = max(1, interval_minutes)

    start_delay_seconds = delay_minutes * 60
    interval_seconds = interval_minutes * 60

    config = {
        "autoplay_enabled": autoplay_enabled,
        "start_delay_seconds": start_delay_seconds,
        "interval_seconds": interval_seconds,
    }

    save_config(config)
    clear_runtime_error()
    app.logger.info(
        "Saved settings: autoplay=%s delay=%ss interval=%ss",
        autoplay_enabled,
        start_delay_seconds,
        interval_seconds,
    )

    stop_player()
    restart_scheduler()

    return redirect("/")


def register_shutdown_handlers():
    global shutdown_handlers_registered

    if shutdown_handlers_registered:
        return

    shutdown_handlers_registered = True

    def shutdown_from_signal(signum, _frame):
        app.logger.info("Received signal %s; stopping playback and disabling MOSFET", signum)
        stop_player()
        raise SystemExit(0)

    def shutdown_from_exit():
        safe_power_off("application exit")

    def handle_unhandled_exception(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            stop_player()
            sys.__excepthook__(exc_type, exc, tb)
            return

        app.logger.critical("Unhandled exception; disabling MOSFET", exc_info=(exc_type, exc, tb))
        safe_power_off("unhandled exception")
        sys.__excepthook__(exc_type, exc, tb)

    signal.signal(signal.SIGTERM, shutdown_from_signal)
    signal.signal(signal.SIGINT, shutdown_from_signal)
    atexit.register(shutdown_from_exit)
    sys.excepthook = handle_unhandled_exception


if __name__ == "__main__":
    register_shutdown_handlers()
    app.logger.info("Starting VTX Player version %s", load_app_version())
    startup_diagnostics = collect_diagnostics()
    for check in startup_diagnostics["checks"]:
        level = logging.INFO if check["ok"] else logging.ERROR
        app.logger.log(level, "Self-check %s: %s", check["label"], check["message"])

    config = load_config()
    if config.get("autoplay_enabled"):
        restart_scheduler()

    app.logger.info("Starting web UI on http://0.0.0.0:8080")
    app.run(host="0.0.0.0", port=8080, threaded=True, use_reloader=False)
