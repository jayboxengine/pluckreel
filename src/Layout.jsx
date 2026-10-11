import { CONTACT_EMAIL, SITE_NAME } from './site'

export function LogoMark() {
  return (
    <span className="vd-logo-mark">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
        strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M12 3v12m0 0 5-5m-5 5-5-5M5 21h14" />
      </svg>
    </span>
  )
}

export function SiteHeader() {
  return (
    <header className="vd-nav">
      <a className="vd-logo" href="/">
        <LogoMark />
        {SITE_NAME}
      </a>
    </header>
  )
}

export function SiteFooter() {
  return (
    <footer className="vd-footer">
      <nav className="vd-footer-links" aria-label="Legal">
        <a href="/terms">Terms of Use</a>
        <a href="/privacy">Privacy Policy</a>
        <a href={`mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(`${SITE_NAME} abuse report`)}`}>
          Report abuse or copyright
        </a>
      </nav>
      For personal, non-commercial use. Please respect each platform&apos;s terms of service and the rights of creators.
      <br />
      {SITE_NAME} is not affiliated with YouTube, TikTok, Meta, X, LinkedIn or Vimeo.
    </footer>
  )
}

export function Page({ children }) {
  return (
    <div className="vd-page">
      <div className="vd-bg" aria-hidden="true" />
      <SiteHeader />
      {children}
      <SiteFooter />
    </div>
  )
}
