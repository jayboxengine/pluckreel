# PluckReel

Paste a link from YouTube, TikTok, Instagram, Facebook, X, LinkedIn or Vimeo and download the
video in any available quality, or just the audio.

- **Frontend:** React + Vite (`src/`) — auto-loads the video as soon as a link is pasted.
- **Backend:** FastAPI + [yt-dlp](https://github.com/yt-dlp/yt-dlp) (`server/`) — fetches formats and
  streams downloads. Where a site serves video and audio separately (all of YouTube), they're merged
  on the fly with ffmpeg into a regular MP4, with nothing written to disk.

ffmpeg and the Deno JS runtime (needed for YouTube's player challenges) are installed from pip, so
there are no system dependencies beyond Python 3.10+ and Node.js.

## Quick start

```powershell
npm install

cd server
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app:app --reload --reload-exclude .venv --port 8000
```

In a second terminal, from the project root:

```powershell
npm run dev
```

Open the URL Vite prints (usually http://localhost:5173). On Linux/macOS use `.venv/bin/python`.

To run it as a single app without Vite, `npm run build` and then only the backend: it serves the
built UI at http://127.0.0.1:8000.

## More

- [server/README.md](server/README.md): background running on Windows (scripts in `local/`),
  cPanel deployment, environment variables and how downloads work.

## Limitations

Private, members-only, age-restricted, region-locked and DRM-protected videos can't be downloaded,
and Instagram, Facebook and LinkedIn often require a logged-in session. Sites change frequently;
when extraction breaks, update yt-dlp first (`pip install -U "yt-dlp[default]"`).

## Disclaimer

For personal, non-commercial use. Respect each platform's terms of service and the rights of
content creators.
