import os
import re
import signal
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

import imageio_ffmpeg
import yt_dlp
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from utils import RateLimiter, is_allowed_url, safe_filename

load_dotenv(Path(__file__).parent / ".env")

# Static ffmpeg shipped as a pip wheel, so this works on shared hosts with no system ffmpeg.
FFMPEG = os.getenv("FFMPEG_PATH") or imageio_ffmpeg.get_ffmpeg_exe()


# YouTube requires solving JS challenges; without a runtime many videos report "not available".
# Deno comes from pip (the `deno` package) so shared hosts need nothing installed; Node is a fallback.
def _js_runtimes() -> dict:
    runtimes = {}
    try:
        import deno
        runtimes["deno"] = {"path": os.getenv("DENO_PATH") or deno.find_deno_bin()}
    except Exception:
        runtimes["deno"] = {"path": os.getenv("DENO_PATH")}
    runtimes["node"] = {"path": os.getenv("NODE_PATH_BIN")}
    return runtimes


JS_RUNTIMES = _js_runtimes()
JS_RUNTIME_ARGS = [a for name, cfg in JS_RUNTIMES.items()
                   for a in ("--js-runtimes", f"{name}:{cfg['path']}" if cfg["path"] else name)]

app = FastAPI()
limiter = RateLimiter(
    limit=int(os.getenv("RATE_LIMIT", "5")),
    window=float(os.getenv("RATE_WINDOW_SECONDS", "60")),
)


def client_ip(request: Request) -> str:
    # Shared hosts sit behind a proxy; trust its first X-Forwarded-For hop.
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")


def check_rate(request: Request):
    if not limiter.allow(client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests, please wait a minute.")


def has(codec) -> bool:
    return codec not in (None, "none")


def size_of(f) -> int:
    return f.get("filesize") or f.get("filesize_approx") or 0


class InfoRequest(BaseModel):
    url: str


@app.post("/api/info")
def video_info(body: InfoRequest, request: Request):
    check_rate(request)
    if not is_allowed_url(body.url):
        raise HTTPException(status_code=400, detail="Unsupported or missing URL")

    opts = {"quiet": True, "no_warnings": True, "noplaylist": True, "socket_timeout": 20,
            "js_runtimes": JS_RUNTIMES}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(body.url, download=False)
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=502, detail=str(e).removeprefix("ERROR: "))

    if info.get("_type") == "playlist":
        entries = [e for e in info.get("entries") or [] if e]
        if not entries:
            raise HTTPException(status_code=404, detail="No videos found at that URL")
        info = entries[0]

    raw = info.get("formats") or [info]
    audio = [f for f in raw if has(f.get("acodec")) and not has(f.get("vcodec"))]
    best_audio = max(audio, key=lambda f: (f.get("ext") == "m4a", f.get("abr") or 0), default=None)
    # Merging needs AAC audio (see /api/download); opus/vorbis-only sources get progressive formats only.
    aac = [f for f in audio if (f.get("acodec") or "").startswith("mp4a")]
    merge_audio = max(aac, key=lambda f: f.get("abr") or 0, default=None)

    # One option per resolution. Progressive (video+audio) formats stream as-is;
    # otherwise the best video-only stream at that height is merged with audio on the fly.
    by_height = {}
    for f in raw:
        if not has(f.get("vcodec")) or not f.get("height"):
            continue
        h = f["height"]
        progressive = has(f.get("acodec"))
        if not progressive and not merge_audio:
            continue
        rank = (progressive, f.get("vcodec", "").startswith("avc1"), f.get("protocol") == "https", f.get("tbr") or 0)
        cur = by_height.get(h)
        if cur is None or rank > cur[0]:
            by_height[h] = (rank, f, progressive)

    formats = []
    for h, (_, f, progressive) in sorted(by_height.items(), reverse=True):
        formats.append({
            "id": f"p-{f['format_id']}" if progressive else f"m-{h}",
            "kind": "video",
            "resolution": f"{h}p",
            "fps": f.get("fps"),
            "ext": f.get("ext") if progressive else "mp4",
            "size": (size_of(f) + (0 if progressive else size_of(merge_audio))) or None,
        })
    if best_audio:
        formats.append({
            "id": f"a-{best_audio['format_id']}",
            "kind": "audio",
            "abr": best_audio.get("abr"),
            "ext": best_audio.get("ext"),
            "size": size_of(best_audio) or None,
        })

    if not formats:
        raise HTTPException(status_code=422, detail="No downloadable formats found for this video")

    return {
        "title": info.get("title") or "video",
        "thumbnail": info.get("thumbnail"),
        "duration": info.get("duration"),
        "uploader": info.get("uploader"),
        "formats": formats,
    }


OPTION_RE = re.compile(r"^(p|a)-([\w-]+)$|^m-(\d{2,4})$")

# Each download runs in its own process group so the whole tree (yt-dlp plus the
# ffmpeg it spawns for merging) can be killed when the client goes away.
_NEW_GROUP = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt"
              else {"start_new_session": True})


def spawn(cmd, **kw):
    return subprocess.Popen(cmd, stderr=subprocess.DEVNULL, **_NEW_GROUP, **kw)


def kill_tree(p: subprocess.Popen):
    if p.poll() is None:
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
            else:
                os.killpg(p.pid, signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
        if p.poll() is None:
            p.kill()
    p.wait()


@app.get("/api/download/{option}")
def download(
    option: str,
    request: Request,
    url: str = Query(...),
    title: str = Query("video"),
    ext: str = Query("mp4"),
):
    check_rate(request)
    if not is_allowed_url(url):
        raise HTTPException(status_code=400, detail="Unsupported URL")
    m = OPTION_RE.match(option)
    if not m:
        raise HTTPException(status_code=400, detail="Invalid format option")

    # Use this interpreter's yt_dlp so it works inside the host's virtualenv without PATH tweaks.
    ytdlp = [sys.executable, "-m", "yt_dlp", "--no-playlist", "--quiet", "--no-part",
             "--ffmpeg-location", FFMPEG, *JS_RUNTIME_ARGS, "-o", "-"]
    if m.group(3):
        h = m.group(3)
        selector = (f"bv*[height={h}][vcodec^=avc1]+ba[acodec^=mp4a]"
                    f"/bv*[height={h}]+ba[acodec^=mp4a]/b[height={h}]")
        # yt-dlp muxes merged formats to stdout as MPEG-TS; remux (no re-encode) into
        # fragmented MP4, which can be written to a pipe and plays in any player.
        # TS carries AAC as ADTS, which MP4 rejects without aac_adtstoasc -- hence AAC-only audio.
        src = spawn(ytdlp + ["-f", selector, url], stdout=subprocess.PIPE)
        proc = spawn(
            [FFMPEG, "-loglevel", "error", "-i", "pipe:0", "-map", "0", "-c", "copy", "-bsf:a", "aac_adtstoasc",
             "-f", "mp4", "-movflags", "frag_keyframe+empty_moov+default_base_moof", "pipe:1"],
            stdin=src.stdout, stdout=subprocess.PIPE,
        )
        src.stdout.close()  # so yt-dlp gets SIGPIPE if ffmpeg exits
        procs, ext, media_type = [proc, src], "mp4", "video/mp4"
    else:
        proc = spawn(ytdlp + ["-f", m.group(2), url], stdout=subprocess.PIPE)
        procs, media_type = [proc], "application/octet-stream"

    async def stream():
        # Async generator: on client disconnect the server cancels it at the await,
        # so the finally block runs (a sync generator would stay blocked in read()).
        try:
            while chunk := await run_in_threadpool(proc.stdout.read, 64 * 1024):
                yield chunk
        finally:
            for p in procs:
                kill_tree(p)

    filename = safe_filename(title, ext)
    return StreamingResponse(
        stream(),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


# Mounted last so /api/* routes take precedence over the SPA catch-all.
_here = Path(__file__).parent
frontend_path = next((p for p in (_here / "static", _here.parent / "dist") if (p / "index.html").exists()), None)
if frontend_path:
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")
