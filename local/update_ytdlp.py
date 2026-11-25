"""Weekly yt-dlp update for the local PluckReel server (run by the "PluckReel yt-dlp update"
scheduled task with the venv's pythonw.exe, so no window appears).

Sites change often and an outdated yt-dlp is the most common reason downloads stop working.
Restarts the server only if the version changed. Results go to server/logs/update.log.
"""
import subprocess
import sys
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

HERE = Path(__file__).parent
SERVER = HERE.parent / "server"
PYTHON = Path(sys.executable).with_name("python.exe")  # console python for pip, run hidden
NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW}
LOG = SERVER / "logs" / "update.log"


def log(msg: str):
    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n")


def current_version() -> str:
    out = subprocess.run([str(PYTHON), "-c", "import yt_dlp.version as v; print(v.__version__)"],
                         capture_output=True, text=True, **NO_WINDOW)
    return out.stdout.strip() or "unknown"


def restart_server():
    out = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, **NO_WINDOW).stdout
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[1] == "127.0.0.1:8000" and parts[3] == "LISTENING":
            subprocess.run(["taskkill", "/F", "/T", "/PID", parts[4]], capture_output=True, **NO_WINDOW)
    # wscript is a GUI program, so this starts the server without a console window.
    subprocess.Popen(["wscript.exe", str(HERE / "start-server.vbs")], **NO_WINDOW)


def main():
    before = current_version()
    result = subprocess.run(
        [str(PYTHON), "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
         "--upgrade", "yt-dlp[default]"],
        capture_output=True, text=True, cwd=SERVER, **NO_WINDOW)
    if result.returncode != 0:
        log(f"update FAILED (still {before}): {result.stderr.strip()[-500:]}")
        return
    after = current_version()
    if after == before:
        log(f"yt-dlp already up to date ({after})")
        return
    restart_server()
    log(f"yt-dlp updated {before} -> {after}; server restarted")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never fail silently: there's no window to show errors
        log(f"update error: {e!r}")
