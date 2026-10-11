import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// Bundled with the site (not Google Fonts) so visitors' IPs aren't sent to a third party.
import '@fontsource-variable/inter'
import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
