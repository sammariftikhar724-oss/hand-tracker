import subprocess

def _run(command: list[str]) -> bool:
    """Command safely run karo aur success check karo."""
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