# PluckReel backend (FastAPI + yt-dlp)

Serves `/api/*` and the built React app from one process, so UI and API share a domain.

## Local development

```powershell
# terminal 1 – API on :8000 (PowerShell; no activation needed)
cd server
python -m venv .venv                                   # first time only
.\.venv\Scripts\python -m pip install -r requirements.txt   # first time only
.\.venv\Scripts\python -m uvicorn app:app --reload --reload-exclude .venv --port 8000

# terminal 2 – Vite on :5173, proxies /api to :8000
npm run dev
```

On Linux/macOS use `.venv/bin/python` instead of `.\.venv\Scripts\python`.

## Everyday local use (Windows, no terminals)

The FastAPI server also serves the built UI, so one hidden process on
http://127.0.0.1:8000 is the whole app — Vite is only needed while editing the UI.
Scripts in `../local/`:

| Script                   | What it does                                                  |
| ------------------------ | ------------------------------------------------------------- |
| `PluckReel.bat`          | Starts the server if needed and opens the app in your browser |
| `enable-autostart.bat`   | Starts the server hidden at every Windows login               |
| `disable-autostart.bat`  | Removes the login autostart                                   |
| `stop-server.bat`        | Stops the background server                                   |

Logs go to `server/logs/server.log`. After changing the UI run `npm run build`; after
changing Python code or upgrading packages, run `stop-server.bat` then start it again.

## Production build

```bash
npm run build                 # writes ../dist
```

`app.py` serves `server/static/` if it exists, otherwise `../dist/`. Upload the
whole `my-app/` folder (minus `node_modules/` and `server/.venv/`) and it will find `dist/`.

## cPanel "Setup Python App"

For cPanel hosts that offer it (Hostinger's hPanel does not; use the VPS setup in the main README).

| Field                    | Value                          |
| ------------------------ | ------------------------------ |
| Python version           | 3.10+                          |
| Application root         | `my-app/server`                |
| Application URL          | your domain                    |
| Application startup file | `passenger_wsgi.py`            |
| Application entry point  | `application`                  |

Then click **Run Pip Install** with `requirements.txt` and restart the app.
Passenger is WSGI, so `passenger_wsgi.py` wraps the FastAPI app with `a2wsgi`.

## Environment (`server/.env`, optional)

| Var                   | Default | Purpose                                     |
| --------------------- | ------- | ------------------------------------------- |
| `RATE_LIMIT`           | `5`     | Requests per IP per window (lookups + download starts) |
| `RATE_WINDOW_SECONDS`  | `60`    | Rate-limit window                                      |
| `MAX_DOWNLOADS`        | `3`     | Simultaneous downloads, overall                        |
| `MAX_DOWNLOADS_PER_IP` | `1`     | Simultaneous downloads per visitor                     |
| `MAX_INFO_LOOKUPS`     | `4`     | Simultaneous video lookups                             |
| `FFMPEG_PATH`          | bundled | Override the ffmpeg from `imageio-ffmpeg`              |

The visitor IP used for limits is the connecting address. Behind a reverse proxy, run uvicorn
with `--proxy-headers --forwarded-allow-ips <proxy IP>` (as `deploy/pluckreel.service` does) so
only the proxy, never a visitor, can set `X-Forwarded-For`.

## How downloads work

- **Progressive** formats (audio+video in one file) and **audio** stream straight from yt-dlp.
- Sites that only offer separate video/audio streams (YouTube, for all resolutions) are
  merged on the fly: yt-dlp → MPEG-TS → ffmpeg remux (no re-encode) → fragmented MP4.
  Nothing is written to disk. Merging requires AAC audio, which all supported sites provide.
- The page first asks `/api/download-ticket` for a single-use token (this is where rate and
  concurrency limits apply, so "busy" shows as a message), then the browser opens
  `/api/download/{token}`. Unused tickets expire after 60 seconds.
- If the client disconnects, the yt-dlp/ffmpeg process tree is killed.
- Thumbnails are fetched by the server and inlined, and the font is bundled, so visitors'
  browsers never contact the platforms or Google.

## Handling copyright and abuse reports

The Terms of Use promise that reported links can be blocked. Add the video's ID (e.g.
`dQw4w9WgXcQ`) or another distinctive part of its URL to `server/blocklist.txt`, one per line;
`#` starts a comment. It takes effect immediately, with no restart, and blocked links get a
"made unavailable at the request of its rights holder" message. On the VPS the file is
`/opt/pluckreel/server/blocklist.txt` (`sudo -u pluckreel nano /opt/pluckreel/server/blocklist.txt`).
Override the path with `BLOCKLIST_FILE`.

The contact email and the "last updated" date on the legal pages are in `src/site.js`.

## Maintenance

YouTube needs a JavaScript runtime to solve its player challenges; without one many videos
fail with "This video is not available". `requirements.txt` installs `yt-dlp[default]` (the
solver scripts) and `deno` (the runtime) from pip, so nothing extra is needed on the host.

Sites change often; when extraction breaks, update yt-dlp first:
`pip install -U "yt-dlp[default]"` (the VPS setup does this weekly automatically).
