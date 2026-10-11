import LegalPage from './LegalPage'
import VideoDownloader from './VideoDownloader'

// Tiny path router: the legal pages are plain links, so no router library is needed.
function App() {
  const path = window.location.pathname.replace(/\/+$/, '')
  if (path === '/terms') return <LegalPage doc="terms" />
  if (path === '/privacy') return <LegalPage doc="privacy" />
  return <VideoDownloader />
}

export default App
