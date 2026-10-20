import platform
import shutil
from device_checker import _run

def _percentage(value: int | float) -> int:
    return max(0, min(100, int(value)))

def set_brightness(value: int | float = 50.0) -> bool:
    value = _percentage(value)
    os_name = platform.system()

    if os_name == "Linux":
        brightnessctl = shutil.which("brightnessctl")
        if brightnessctl and _run([brightnessctl, "set", f"{value}%"]):
            return True
        print("Linux brightness unavailable. Check brightnessctl installation.")
        return False

    return False