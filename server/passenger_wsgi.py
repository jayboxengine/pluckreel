# Entry point for cPanel "Setup Python App" (Phusion Passenger speaks WSGI, FastAPI is ASGI).
# In cPanel set: Application startup file = passenger_wsgi.py, Entry point = application
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from a2wsgi import ASGIMiddleware  # noqa: E402
from app import app  # noqa: E402

application = ASGIMiddleware(app)
