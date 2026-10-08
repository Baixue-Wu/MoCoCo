import { AnalysisExample } from "./screens/AnalysisExample"
import { Link, Route, Routes } from 'react-router-dom'
import { useI18n } from './i18n'
import { LangToggle } from './components/LangToggle'
import { Home } from './screens/Home'
import { ProjectScreen } from './screens/Project'
import { SherlockJrExample } from './screens/SherlockJrExample'
import { BrowserProjectScreen } from './screens/BrowserProject'

const publicMode = import.meta.env.MODE === 'public'

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
          <Route path="/examples/sintel-analysis" element={<AnalysisExample />} />
          <Route path="/examples/sherlock-jr/*" element={<SherlockJrExample />} />
          <Route path="/p/:slug/*" element={publicMode ? <BrowserProjectScreen /> : <ProjectScreen />} />
        </Routes>
      </main>
    </div>
  )
}
