import base64
import logging
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from urllib.parse import quote

import imageio_ffmpeg
import yt_dlp
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from utils import Blocklist, DownloadSlots, RateLimiter, is_allowed_url, safe_filename

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
# Each download runs yt-dlp (+ ffmpeg when merging), so concurrency is what a small server runs out of.
log = logging.getLogger("pluckreel")
slots = DownloadSlots(
    total=int(os.getenv("MAX_DOWNLOADS", "3")),
    per_ip=int(os.getenv("MAX_DOWNLOADS_PER_IP", "1")),
    on_expire=lambda procs: [kill_tree(p) for p in procs],
)
# Metadata lookups are lighter but still a few seconds of CPU and network each.
info_slots = threading.BoundedSemaphore(int(os.getenv("MAX_INFO_LOOKUPS", "4")))

THUMB_MAX_BYTES = 1_500_000

blocklist = Blocklist(os.getenv("BLOCKLIST_FILE") or Path(__file__).parent / "blocklist.txt")
BLOCKED_DETAIL = "This video has been made unavailable here at the request of its rights holder."


def client_ip(request: Request) -> str:
    # The connecting peer, never a client-supplied header. Behind a reverse proxy, uvicorn's
    # proxy-headers support rewrites this from X-Forwarded-For, but only for proxies listed in
    # --forwarded-allow-ips (default 127.0.0.1), so visitors can't spoof it.
    return request.client.host if request.client else "?"


def check_rate(request: Request):
    if not limiter.allow(client_ip(request)):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait a minute and try again.")


def has(codec) -> bool:
    return codec not in (None, "none")


def size_of(f) -> int:
    return f.get("filesize") or f.get("filesize_approx") or 0


def pick_thumbnail(info) -> str | None:
    """A thumbnail around 480px wide where the site offers sizes, else the default one."""
    thumbs = [t for t in info.get("thumbnails") or [] if (t.get("url") or "").startswith("https://")]
    sized = [t for t in thumbs if t.get("width")]
    if sized:
        return min(sized, key=lambda t: abs(t["width"] - 480))["url"]
    url = info.get("thumbnail")
    return url if url and url.startswith("https://") else (thumbs[-1]["url"] if thumbs else None)


def fetch_thumbnail(ydl, url: str | None) -> str | None:
    """Fetch the thumbnail server-side and inline it as a data URL, so visitors' browsers never
    contact the platforms' image servers (which would hand them visitors' IP addresses)."""
    if not url:
        return None
    try:
        with ydl.urlopen(url) as resp:
            ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip()
            data = resp.read(THUMB_MAX_BYTES + 1)
    except Exception:
        return None
    if not ctype.startswith("image/") or len(data) > THUMB_MAX_BYTES:
        return None
    return f"data:{ctype};base64,{base64.b64encode(data).decode()}"


# Facebook titles start with engagement counts: "43 reactions · 12 shares | Actual text".
_ENGAGEMENT_PREFIX = re.compile(
    r"^\s*(?:[\d.,]+\s*[KkMm]?\s+(?:reactions?|shares?|comments?|views?|likes?)\s*[·•,]?\s*)+\|\s*")


def clean_title(title: str | None) -> str:
    title = _ENGAGEMENT_PREFIX.sub("", title or "").strip()
    return title or "video"


class InfoRequest(BaseModel):
    url: str = Field(max_length=2048)


@app.post("/api/info")
def video_info(body: InfoRequest, request: Request):
    check_rate(request)
    if not is_allowed_url(body.url):
        raise HTTPException(status_code=400, detail="Unsupported or missing URL")
    if blocklist.is_blocked(body.url):
        raise HTTPException(status_code=451, detail=BLOCKED_DETAIL)
    if not info_slots.acquire(timeout=15):
        raise HTTPException(status_code=503, detail="The server is busy right now. Please try again in a moment.")
    try:
        return _video_info(body.url)
    finally:
        info_slots.release()


def _video_info(url: str):
    opts = {"quiet": True, "no_warnings": True, "noplaylist": True, "socket_timeout": 20,
            "js_runtimes": JS_RUNTIMES}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if info.get("_type") == "playlist":
                entries = [e for e in info.get("entries") or [] if e]
                if not entries:
                    raise HTTPException(status_code=404, detail="No videos found at that URL")
                info = entries[0]
            thumbnail = fetch_thumbnail(ydl, pick_thumbnail(info))
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=502, detail=str(e).removeprefix("ERROR: "))

    raw = info.get("formats") or [info]
    audio = [f for f in raw if has(f.get("acodec")) and not has(f.get("vcodec"))]
    best_audio = max(audio, key=lambda f: (f.get("ext") == "m4a", f.get("abr") or 0), default=None)
    # Audio used when merging (sizes only; /api/download picks the same way): AAC preferred.
    merge_audio = max(audio, key=lambda f: ((f.get("acodec") or "").startswith("mp4a"), f.get("abr") or 0),
                      default=None)

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
        "title": clean_title(info.get("title")),
        "thumbnail": thumbnail,
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
    kw.setdefault("stderr", subprocess.DEVNULL)
    return subprocess.Popen(cmd, **_NEW_GROUP, **kw)


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


class TicketRequest(BaseModel):
    url: str = Field(max_length=2048)
    option: str = Field(max_length=64)
    title: str = "video"
    ext: str = Field(default="mp4", max_length=10)

    @field_validator("title", mode="before")
    @classmethod
    def _shorten_title(cls, v):
        # Only used for the file name (cut to 120 chars there); long titles such as Facebook
        # post text must not make the request fail.
        return str(v or "video")[:300]


@app.post("/api/download-ticket")
def download_ticket(body: TicketRequest, request: Request):
    """Reserve a download slot. The page then navigates to /api/download/{token}."""
    check_rate(request)
    if not is_allowed_url(body.url):
        raise HTTPException(status_code=400, detail="Unsupported URL")
    if blocklist.is_blocked(body.url):
        raise HTTPException(status_code=451, detail=BLOCKED_DETAIL)
    if not OPTION_RE.match(body.option):
        raise HTTPException(status_code=400, detail="Invalid format option")
    token, reason = slots.reserve(client_ip(request), body.model_dump())
    if reason == "per_ip":
        raise HTTPException(status_code=429, detail="You already have a download in progress. Please wait for it to finish.")
    if reason == "busy":
        raise HTTPException(status_code=503, detail="The server is busy with other downloads. Please try again in a minute.")
    return {"token": token}


REMUX_TO_MP4 = [FFMPEG, "-loglevel", "error", "-i", "pipe:0", "-map", "0", "-c", "copy", "-f", "mp4",
                "-movflags", "frag_keyframe+empty_moov+default_base_moof", "pipe:1"]


def _err_tail(f, limit=1500) -> str:
    try:
        f.seek(0)
        return f.read().decode("utf-8", "replace").strip()[-limit:]
    except Exception:
        return ""


@app.get("/api/download/{token}")
async def download(token: str):
    job = slots.claim(token)
    if not job:
        raise HTTPException(status_code=410, detail="This download link has expired. Please click Download again.")
    m = OPTION_RE.match(job["option"])
    url, ext = job["url"], job["ext"]
    merge_height = m.group(3)

    # Use this interpreter's yt_dlp so it works inside the host's virtualenv without PATH tweaks.
    ytdlp = [sys.executable, "-m", "yt_dlp", "--no-playlist", "--quiet", "--no-part",
             "--ffmpeg-location", FFMPEG, *JS_RUNTIME_ARGS, "-o", "-"]
    errs = [tempfile.TemporaryFile() for _ in range(2)]
    procs = []
    try:
        if merge_height:
            h = merge_height
            # Prefer H.264 + AAC (plays everywhere); otherwise take whatever the site has
            # (Instagram and YouTube's top resolutions are often VP9 or AV1 only).
            selector = (f"bv*[height={h}][vcodec^=avc1]+ba[acodec^=mp4a]/bv*[height={h}][vcodec^=avc1]+ba"
                        f"/bv*[height={h}]+ba[acodec^=mp4a]/bv*[height={h}]+ba/b[height={h}]")
            # yt-dlp merges to stdout as Matroska here (for an .mp4 target it would use MPEG-TS,
            # which can't carry VP9/AV1, so the video track was lost). ffmpeg then remuxes,
            # without re-encoding, into fragmented MP4, which can be written to a pipe.
            src = spawn(ytdlp + ["--merge-output-format", "mkv", "-f", selector, url],
                        stdout=subprocess.PIPE, stderr=errs[0])
            procs.append(src)
            proc = spawn(REMUX_TO_MP4, stdin=src.stdout, stdout=subprocess.PIPE, stderr=errs[1])
            src.stdout.close()  # so yt-dlp gets SIGPIPE if ffmpeg exits
            procs.insert(0, proc)
            ext, media_type = "mp4", "video/mp4"
        else:
            proc = spawn(ytdlp + ["-f", m.group(2), url], stdout=subprocess.PIPE, stderr=errs[0])
            procs.append(proc)
            media_type = "application/octet-stream"
        # If the client vanishes before streaming starts, the slot expiry kills these.
        slots.attach(token, procs)

        # Wait for the first bytes before answering, so a failed download shows as a failed
        # download in the browser instead of an empty file.
        first = await run_in_threadpool(proc.stdout.read, 64 * 1024)
    except BaseException:
        for p in procs:
            kill_tree(p)
        slots.release(token)
        raise
    if not first:
        for p in procs:
            kill_tree(p)
        slots.release(token)
        log.warning("Download failed for %s (%s): %s | %s", url, job["option"],
                    _err_tail(errs[0]), _err_tail(errs[1]))
        raise HTTPException(status_code=502, detail="The download failed. The site may be blocking requests right now; please try again later.")

    async def stream():
        # Async generator: on client disconnect the server cancels it at the await,
        # so the finally block runs (a sync generator would stay blocked in read()).
        slots.start(token)
        try:
            yield first
            while chunk := await run_in_threadpool(proc.stdout.read, 64 * 1024):
                yield chunk
        finally:
            for p in procs:
                kill_tree(p)
            for f in errs:
                f.close()
            slots.release(token)

    filename = safe_filename(job["title"], ext)
    return StreamingResponse(
        stream(),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


# Mounted last so /api/* routes take precedence over the SPA catch-all.
_here = Path(__file__).parent
frontend_path = next((p for p in (_here / "static", _here.parent / "dist") if (p / "index.html").exists()), None)
if frontend_path:
    # Client-side pages: serve the app shell, which renders the right page for the path.
    @app.get("/terms", include_in_schema=False)
    @app.get("/terms/", include_in_schema=False)
    @app.get("/privacy", include_in_schema=False)
    @app.get("/privacy/", include_in_schema=False)
    def spa_page():
        return FileResponse(frontend_path / "index.html")

    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")
