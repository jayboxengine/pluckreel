"""Run the app locally as a single background process (API + built UI on http://127.0.0.1:8000).

Started windowless by local/start-server.vbs (pythonw has no console), so all output goes to
logs/server.log. Exits immediately if something is already listening on the port.
"""
import logging
import os
import socket
import sys
from pathlib import Path

HERE = Path(__file__).parent
HOST, PORT = "127.0.0.1", int(os.getenv("PORT", "8000"))


def port_in_use() -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((HOST, PORT)) == 0


if __name__ == "__main__":
    if port_in_use():
        sys.exit(0)

    os.chdir(HERE)
    sys.path.insert(0, str(HERE))
    # Local use: the public-site limit of 5 requests/min is needlessly tight.
    os.environ.setdefault("RATE_LIMIT", "60")

    logs = HERE / "logs"
    logs.mkdir(exist_ok=True)
    log = open(logs / "server.log", "a", buffering=1, encoding="utf-8")
    sys.stdout = sys.stderr = log
    logging.basicConfig(stream=log, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    import uvicorn

    uvicorn.run("app:app", host=HOST, port=PORT, log_config=None, use_colors=False)
