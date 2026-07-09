import logging
import threading


GPIO_PIN = 17

_lock = threading.RLock()
_device = None
_backend = "unavailable"
_error = ""
_powered = False


class GPIOError(RuntimeError):
    """Raised when GPIO17 power-switch control is not available."""


def _initialize():
    global _backend, _device, _error

    backend_errors = (ImportError, RuntimeError, OSError, ValueError)

    with _lock:
        if _device is not None or _error:
            return

        try:
            from gpiozero import Device, OutputDevice
            from gpiozero.exc import GPIOZeroError

            backend_errors = backend_errors + (GPIOZeroError,)

            try:
                from gpiozero.pins.lgpio import LGPIOFactory

                Device.pin_factory = LGPIOFactory()
                _backend = "lgpio"
            except backend_errors as exc:
                _backend = "gpiozero default"
                logging.getLogger(__name__).warning(
                    "LGPIO backend unavailable, using gpiozero default backend: %s",
                    exc,
                )

            _device = OutputDevice(GPIO_PIN, active_high=True, initial_value=False)
            _backend = getattr(Device.pin_factory, "__class__", type(Device.pin_factory)).__name__
            _set_powered(False)
        except Exception as exc:
            _device = None
            _backend = "unavailable"
            _error = str(exc)
            logging.getLogger(__name__).error("GPIO17 initialization failed: %s", exc)


def _set_powered(value):
    global _powered
    _powered = bool(value)


def _gpio_exception_types():
    errors = (RuntimeError, OSError, ValueError)

    try:
        from gpiozero.exc import GPIOZeroError

        errors = errors + (GPIOZeroError,)
    except ImportError:
        pass

    try:
        import lgpio

        errors = errors + (lgpio.error,)
    except (ImportError, AttributeError):
        pass

    return errors


def is_available():
    _initialize()
    with _lock:
        return _device is not None and not _error


def status():
    _initialize()

    with _lock:
        if _device is None:
            return {
                "ok": False,
                "pin": GPIO_PIN,
                "backend": _backend,
                "powered": False,
                "error": _error or "GPIO device was not initialized.",
            }

        return {
            "ok": True,
            "pin": GPIO_PIN,
            "backend": _backend,
            "powered": _powered,
            "error": "",
        }


def power_on():
    _initialize()

    with _lock:
        if _device is None:
            raise GPIOError(_error or "GPIO17 is not available.")

        _device.on()
        _set_powered(True)


def power_off():
    _initialize()

    with _lock:
        if _device is None:
            _set_powered(False)
            return

        try:
            _device.off()
        except _gpio_exception_types() as exc:
            logging.getLogger(__name__).warning("GPIO17 power-off skipped: %s", exc)
        finally:
            _set_powered(False)


def cleanup():
    with _lock:
        try:
            power_off()
        finally:
            if _device is not None:
                _device.close()
