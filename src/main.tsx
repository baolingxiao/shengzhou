import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './app/App'
import { installGlobalTraceHooks } from './lib/debugTrace'
import './styles/globals.css'

installGlobalTraceHooks()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
