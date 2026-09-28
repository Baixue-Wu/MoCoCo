import { Link, Route, Routes } from 'react-router-dom'
import { useI18n } from './i18n'
import { LangToggle } from './components/LangToggle'
import { Home } from './screens/Home'
import { ProjectScreen } from './screens/Project'

export default function App() {
  const { t } = useI18n()
  return (
    <div>
      <header className="app-header">
        <Link to="/" className="app-brand">
          <h1 style={{ margin: 0 }}>{t('app.title')}</h1>
          <span className="tagline">{t('app.tagline')}</span>
        </Link>
        <LangToggle />
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/p/:slug/*" element={<ProjectScreen />} />
        </Routes>
      </main>
    </div>
  )
}
