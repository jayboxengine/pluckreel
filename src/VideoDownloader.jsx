import { useEffect, useRef, useState } from 'react'
import './VideoDownloader.css'

// Mirrors ALLOWED_HOSTS in server/utils.py
const PLATFORMS = [
  { name: 'YouTube', hosts: ['youtube.com', 'youtu.be'], color: '#ff0033' },
  { name: 'TikTok', hosts: ['tiktok.com'], color: '#00c2c7' },
  { name: 'Instagram', hosts: ['instagram.com'], color: '#e1306c' },
  { name: 'Facebook', hosts: ['facebook.com', 'fb.watch'], color: '#1877f2' },
  { name: 'X', hosts: ['x.com', 'twitter.com'], color: '#7c7c8f' },
  { name: 'LinkedIn', hosts: ['linkedin.com'], color: '#0a66c2' },
  { name: 'Vimeo', hosts: ['vimeo.com'], color: '#17a9e0' },
]

const AUTO_FETCH_DELAY = 350

function parseUrl(text) {
  try {
    const u = new URL(text.trim())
    return /^https?:$/.test(u.protocol) ? u : null
  } catch {
    return null
  }
}

function detectPlatform(text) {
  const u = parseUrl(text)
  if (!u) return null
  const host = u.hostname.toLowerCase()
  return PLATFORMS.find((p) => p.hosts.some((h) => host === h || host.endsWith('.' + h))) || null
}

function formatSize(bytes) {
  if (!bytes) return null
  if (bytes >= 1024 ** 3) return `${(bytes / 1024 ** 3).toFixed(1)} GB`
  if (bytes >= 1024 ** 2) return `${Math.round(bytes / 1024 ** 2)} MB`
  return `${Math.max(1, Math.round(bytes / 1024))} KB`
}

function formatDuration(sec) {
  if (!sec) return ''
  const s = Math.round(sec)
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const ss = String(s % 60).padStart(2, '0')
  return h ? `${h}:${String(m).padStart(2, '0')}:${ss}` : `${m}:${ss}`
}

function qualityTag(resolution) {
  const h = parseInt(resolution, 10) || 0
  if (h >= 2160) return '4K'
  if (h >= 1440) return '2K'
  if (h >= 1080) return 'Full HD'
  if (h >= 720) return 'HD'
  return null
}

async function errorMessage(res) {
  try {
    const body = await res.json()
    // yt-dlp errors look like "[youtube] abc123: This video is not available"
    if (typeof body.detail === 'string') return body.detail.replace(/^\[[^\]]+\]\s*[^:\s]+:\s*/, '')
  } catch {
    // not JSON
  }
  // A non-JSON 502/503/504 comes from the proxy, not FastAPI: the backend isn't reachable.
  if ([502, 503, 504].includes(res.status)) {
    return "Can't reach the download server. Make sure the backend is running."
  }
  return `Something went wrong (${res.status}).`
}

const Icon = {
  link: (
    <path d="M10 13a5 5 0 0 0 7.07 0l3-3a5 5 0 0 0-7.07-7.07l-1.5 1.5M14 11a5 5 0 0 0-7.07 0l-3 3a5 5 0 0 0 7.07 7.07l1.5-1.5" />
  ),
  paste: (
    <>
      <rect x="8" y="2" width="8" height="4" rx="1" />
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
    </>
  ),
  x: <path d="M18 6 6 18M6 6l12 12" />,
  download: <path d="M12 3v12m0 0 5-5m-5 5-5-5M5 21h14" />,
  check: <path d="m5 12 5 5L20 7" />,
  alert: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v4m0 4h.01" />
    </>
  ),
  film: (
    <>
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M7 3v18M17 3v18M3 8h4M3 16h4M17 8h4M17 16h4M3 12h18" />
    </>
  ),
  music: (
    <>
      <path d="M9 18V5l12-2v13" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="16" r="3" />
    </>
  ),
}

function Svg({ name, size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {Icon[name]}
    </svg>
  )
}

export default function VideoDownloader() {
  // ?url=<link> pre-fills the box (handy for bookmarklets / share links); it then auto-loads.
  const [url, setUrl] = useState(() => new URLSearchParams(window.location.search).get('url') ?? '')
  const [status, setStatus] = useState('idle') // idle | loading | done | error
  const [info, setInfo] = useState(null)
  const [error, setError] = useState('')
  const [fetchedUrl, setFetchedUrl] = useState('')
  const [tab, setTab] = useState('video')
  const [preparing, setPreparing] = useState(null)
  const [dlError, setDlError] = useState('')
  const lastRequested = useRef('')
  const abortRef = useRef(null)
  const inputRef = useRef(null)

  const platform = detectPlatform(url)
  const looksLikeUrl = !!parseUrl(url)
  const canPaste = typeof navigator !== 'undefined' && !!navigator.clipboard?.readText

  const load = async (target) => {
    lastRequested.current = target
    abortRef.current?.abort()
    const ctrl = new AbortController()
    abortRef.current = ctrl
    setStatus('loading')
    setError('')
    setDlError('')
    setInfo(null)
    try {
      const res = await fetch('/api/info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: target }),
        signal: ctrl.signal,
      })
      if (!res.ok) throw new Error(await errorMessage(res))
      const data = await res.json()
      setInfo(data)
      setFetchedUrl(target)
      setTab(data.formats.some((f) => f.kind === 'video') ? 'video' : 'audio')
      setStatus('done')
    } catch (err) {
      if (err.name === 'AbortError') return
      setError(err.message)
      setStatus('error')
    }
  }

  // Auto-load as soon as a supported link is pasted or typed (debounced, never twice for the same URL).
  useEffect(() => {
    const target = url.trim()
    if (!detectPlatform(target) || target === lastRequested.current) return
    const t = setTimeout(() => load(target), AUTO_FETCH_DELAY)
    return () => clearTimeout(t)
  }, [url])

  useEffect(() => () => abortRef.current?.abort(), [])

  const reset = () => {
    abortRef.current?.abort()
    lastRequested.current = ''
    setUrl('')
    setInfo(null)
    setError('')
    setStatus('idle')
    inputRef.current?.focus()
  }

  const pasteFromClipboard = async () => {
    try {
      const text = await navigator.clipboard.readText()
      if (text) setUrl(text.trim())
    } catch {
      inputRef.current?.focus()
    }
  }

  // Reserve a download slot first, so "busy" / "rate limited" show here as messages instead of
  // as a failed file in the browser's download bar; then hand the one-time link to the browser.
  const startDownload = async (f) => {
    if (preparing) return
    setPreparing(f.id)
    setDlError('')
    try {
      const res = await fetch('/api/download-ticket', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: fetchedUrl, option: f.id, title: info.title, ext: f.ext }),
      })
      if (!res.ok) throw new Error(await errorMessage(res))
      const { token } = await res.json()
      const a = document.createElement('a')
      a.href = `/api/download/${encodeURIComponent(token)}`
      a.download = ''
      document.body.appendChild(a)
      a.click()
      a.remove()
      setTimeout(() => setPreparing((cur) => (cur === f.id ? null : cur)), 8000)
    } catch (err) {
      setDlError(err.message)
      setPreparing(null)
    }
  }

  const unsupported = url.trim() && looksLikeUrl && !platform
  const videos = info?.formats.filter((f) => f.kind === 'video') ?? []
  const audios = info?.formats.filter((f) => f.kind === 'audio') ?? []
  const shown = tab === 'video' ? videos : audios

  return (
    <div className="vd-page">
      <div className="vd-bg" aria-hidden="true" />

      <header className="vd-nav">
        <div className="vd-logo">
          <span className="vd-logo-mark"><Svg name="download" size={16} /></span>
          PluckReel
        </div>
      </header>

      <main className="vd-main">
        <section className="vd-hero">
          <span className="vd-eyebrow">Fast · Free · No sign-up</span>
          <h1>
            Download videos from <span className="vd-grad">anywhere</span>
          </h1>
          <p className="vd-lead">Paste a link and we&apos;ll fetch every available quality automatically.</p>

          <div className={`vd-search${status === 'loading' ? ' is-loading' : ''}`}>
            <span className="vd-search-icon" style={platform ? { color: platform.color } : undefined}>
              <Svg name="link" />
            </span>
            <input
              ref={inputRef}
              type="url"
              inputMode="url"
              placeholder="Paste a video link…"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && platform && load(url.trim())}
              aria-label="Video URL"
              autoFocus
              spellCheck="false"
            />
            {platform && <span className="vd-platform-pill">{platform.name}</span>}
            {status === 'loading' ? (
              <span className="vd-spinner" role="status" aria-label="Loading" />
            ) : url ? (
              <button type="button" className="vd-icon-btn" onClick={reset} aria-label="Clear">
                <Svg name="x" size={18} />
              </button>
            ) : (
              canPaste && (
                <button type="button" className="vd-paste-btn" onClick={pasteFromClipboard}>
                  <Svg name="paste" size={16} /> Paste
                </button>
              )
            )}
          </div>

          <p className={`vd-hint${unsupported ? ' is-warn' : ''}`}>
            {unsupported
              ? 'That site isn’t supported yet. Try one of the platforms below.'
              : 'Works with'}
          </p>
          <ul className="vd-chips">
            {PLATFORMS.map((p) => (
              <li key={p.name} className={platform?.name === p.name ? 'is-active' : ''}>
                <span className="vd-dot" style={{ background: p.color }} />
                {p.name}
              </li>
            ))}
          </ul>
        </section>

        <section className="vd-output" aria-live="polite">
          {status === 'loading' && (
            <div className="vd-card vd-skeleton">
              <div className="vd-sk-thumb" />
              <div className="vd-sk-body">
                <div className="vd-sk-line w80" />
                <div className="vd-sk-line w40" />
                <div className="vd-sk-row" />
                <div className="vd-sk-row" />
                <div className="vd-sk-row" />
              </div>
            </div>
          )}

          {status === 'error' && (
            <div className="vd-card vd-error">
              <span className="vd-error-icon"><Svg name="alert" /></span>
              <div>
                <h3>Couldn&apos;t load this video</h3>
                <p>{error}</p>
              </div>
              <button type="button" className="vd-btn-ghost" onClick={() => load(url.trim())}>
                Try again
              </button>
            </div>
          )}

          {status === 'done' && info && (
            <article className="vd-card vd-result">
              <div className="vd-thumb">
                {info.thumbnail ? (
                  <img src={info.thumbnail} alt="" referrerPolicy="no-referrer" />
                ) : (
                  <div className="vd-thumb-empty"><Svg name="film" size={32} /></div>
                )}
                {info.duration ? <span className="vd-duration">{formatDuration(info.duration)}</span> : null}
              </div>

              <div className="vd-result-body">
                <div className="vd-result-head">
                  <h2 title={info.title}>{info.title}</h2>
                  {info.uploader && <p>{info.uploader}</p>}
                </div>

                <div className="vd-tabs" role="tablist">
                  <button type="button" role="tab" aria-selected={tab === 'video'}
                    disabled={!videos.length} onClick={() => setTab('video')}>
                    <Svg name="film" size={16} /> Video <span>{videos.length}</span>
                  </button>
                  <button type="button" role="tab" aria-selected={tab === 'audio'}
                    disabled={!audios.length} onClick={() => setTab('audio')}>
                    <Svg name="music" size={16} /> Audio <span>{audios.length}</span>
                  </button>
                </div>

                <ul className="vd-formats">
                  {shown.map((f) => {
                    const tag = f.kind === 'video' ? qualityTag(f.resolution) : null
                    const size = formatSize(f.size)
                    return (
                      <li key={f.id}>
                        <div className="vd-format-main">
                          <strong>{f.kind === 'video' ? f.resolution : `${f.abr ? Math.round(f.abr) + ' kbps' : 'Audio'}`}</strong>
                          {tag && <span className="vd-tag">{tag}</span>}
                        </div>
                        <span className="vd-format-meta">
                          {f.ext?.toUpperCase()}
                          {f.fps && f.fps > 30 ? ` · ${f.fps}fps` : ''}
                          {size ? ` · ${size}` : ''}
                        </span>
                        <button type="button" className={`vd-dl${preparing === f.id ? ' is-preparing' : ''}`}
                          disabled={!!preparing && preparing !== f.id} onClick={() => startDownload(f)}>
                          {preparing === f.id ? <><Svg name="check" size={16} /> Starting…</> : <><Svg name="download" size={16} /> Download</>}
                        </button>
                      </li>
                    )
                  })}
                </ul>
                {dlError ? (
                  <p className="vd-note is-error" role="alert">{dlError}</p>
                ) : preparing && (
                  <p className="vd-note">Preparing your file. The download will appear in your browser shortly.</p>
                )}
              </div>
            </article>
          )}
        </section>
      </main>

      <footer className="vd-footer">
        For personal, non-commercial use. Please respect each platform&apos;s terms of service and the rights of creators.
        <br />
        PluckReel is not affiliated with YouTube, TikTok, Meta, X, LinkedIn or Vimeo.
      </footer>
    </div>
  )
}
