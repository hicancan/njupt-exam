import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { registerSW } from 'virtual:pwa-register'
import './index.css'
import App from './App'



const rootElement = document.getElementById('root')
if (!rootElement) {
  throw new Error("Failed to find the root element")
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

const updateServiceWorker = registerSW({
  immediate: true,
  onNeedRefresh() {
    void updateServiceWorker(true)
  },
  onRegisterError(error) {
    console.error('Service worker registration failed:', error)
  }
})
