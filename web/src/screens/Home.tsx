import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import * as api from '../api'
import { useI18n } from '../i18n'
import { useToast } from '../components/Toast'
import { Spinner } from '../components/Spinner'
import { ProgressDots } from '../components/ProgressDots'
import { NewProjectForm } from './NewProjectForm'
import { allSteps } from '../state/steps'
import { listBrowserProjects, type BrowserProject } from '../browserProjects'

const publicMode = import.meta.env.MODE === 'public'

export function Home() {
  const { t } = useI18n()
  const { showError } = useToast()
  const navigate = useNavigate()
  const [projects, setProjects] = useState<api.ProjectSummary[] | null>(null)
  const [browserProjects, setBrowserProjects] = useState<BrowserProject[] | null>(null)
  const [showForm, setShowForm] = useState(false)

  const load = useCallback(() => {
    if (publicMode) listBrowserProjects().then(setBrowserProjects).catch(showError)
    else api.listProjects().then(setProjects).catch(showError)
  }, [showError])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div>
      <div className="row-between" style={{ marginBottom: 22 }}>
        <div>
          <h1>{t('home.heading')}</h1>
          <p className="muted">{t('home.subtitle')}</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(true)}>
          {t('home.new_project')}
        </button>
      </div>

      <section className="featured-example card">
        <img src="https://baixue-wu.github.io/MoCoCo/assets/sherlock-jr-poster.jpg" alt="《福尔摩斯二世》电影画面" />
        <div>
          <span className="badge badge-accent">{t('example.badge')}</span>
          <h2>{t('example.title')}</h2>
          <p className="muted">{t('example.summary')}</p>
          <Link className="btn btn-primary" to="/examples/sherlock-jr">{t('example.browse')}</Link>
        </div>
      </section>

      {(publicMode ? browserProjects === null : projects === null) && (
        <div className="center-msg">
          <Spinner />
        </div>
      )}

      {(publicMode ? browserProjects?.length === 0 : projects?.length === 0) && <div className="center-msg">{t('home.empty')}</div>}

      {publicMode && browserProjects !== null && browserProjects.length > 0 && (
        <div className="grid-cards">
          {browserProjects.map((p) => (
            <Link key={p.slug} to={`/p/${p.slug}`} className="card project-card">
              <div className="row-between">
                <h2 style={{ margin: 0 }}>{p.title}</h2>
                <span className="badge badge-accent">{t('browser.local_badge')}</span>
              </div>
              <span className="small muted">{p.film_name}</span>
              <span className="small muted">{new Date(p.created * 1000).toLocaleDateString()}</span>
            </Link>
          ))}
        </div>
      )}

      {!publicMode && projects !== null && projects.length > 0 && (
        <div className="grid-cards">
          {projects.map((p) => (
            <Link key={p.slug} to={`/p/${p.slug}`} className="card project-card">
              <div className="row-between">
                <h2 style={{ margin: 0 }}>{p.title}</h2>
                <span className="badge badge-accent">{p.style}</span>
              </div>
              <ProgressDots steps={allSteps(p.status)} />
              <span className="small muted">{new Date(p.created * 1000).toLocaleDateString()}</span>
            </Link>
          ))}
        </div>
      )}

      {showForm && (
        <NewProjectForm
          onClose={() => setShowForm(false)}
          onCreated={(slug) => {
            setShowForm(false)
            navigate(`/p/${slug}`)
          }}
        />
      )}
    </div>
  )
}
