# volume_control.py
import platform
import shutil
import subprocess
import numpy as np
def _run(command: list[str]) -> bool:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False

def _percentage(value: int | float) -> int:
    return max(0, min(100, int(value)))

def set_volume(value: int | float) -> bool:
    value = _percentage(value)
    os_name = platform.system()

    if os_name == "Linux":
        pactl = shutil.which("pactl")
        if pactl and _run([pactl, "set-sink-volume", "@DEFAULT_SINK@", f"{value}%"]):
            return True

        wpctl = shutil.which("wpctl")
        if wpctl and _run([wpctl, "set-volume", "@DEFAULT_AUDIO_SINK@", f"{value}%"]):
            return True

        amixer = shutil.which("amixer")
        if amixer and _run([amixer, "sset", "Master", f"{value}%"]):
            return True
        return False

    elif os_name == "Windows":
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            import ctypes

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(value / 100.0, None)
            return True
        except Exception:
            return False

    return False

def mouse_control(action: str, x: int = 0, y: int = 0) -> bool:
    """Mouse movement aur click control function."""
    try:
        import pyautogui
        pyautogui.FAILSAFE = False

        if action == "move":
            # Screen resolution ke mutabiq scale karein
            screen_w, screen_h = pyautogui.size()
            # Assuming camera frame is 640x480
            target_x = np.interp(x, (50, 590), (0, screen_w))
            target_y = np.interp(y, (50, 430), (0, screen_h))
            pyautogui.moveTo(target_x, target_y, duration=0.01)
        elif action == "click":
            pyautogui.click()
        return True
    except Exception:
        return False