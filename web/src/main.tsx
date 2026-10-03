import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { BrowserRouter, HashRouter } from 'react-router-dom'
import App from './App.tsx'
import { I18nProvider } from './i18n'
import { ToastProvider } from './components/Toast'

const Router = import.meta.env.MODE === 'public' ? HashRouter : BrowserRouter

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <I18nProvider>
      <ToastProvider>
        <Router>
          <App />
        </Router>
      </ToastProvider>
    </I18nProvider>
  </StrictMode>,
)
