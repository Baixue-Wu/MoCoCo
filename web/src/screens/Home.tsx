import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import * as api from '../api'
import { useI18n } from '../i18n'
import { useToast } from '../components/Toast'
import { Spinner } from '../components/Spinner'
import { ProgressDots } from '../components/ProgressDots'
import { NewProjectForm } from './NewProjectForm'
import { allSteps } from '../state/steps'

export function Home() {
  const { t } = useI18n()
  const { showError } = useToast()
  const navigate = useNavigate()
  const [projects, setProjects] = useState<api.ProjectSummary[] | null>(null)
  const [showForm, setShowForm] = useState(false)

  const load = useCallback(() => {
    api.listProjects().then(setProjects).catch(showError)
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

      {projects === null && (
        <div className="center-msg">
          <Spinner />
        </div>
      )}

      {projects !== null && projects.length === 0 && <div className="center-msg">{t('home.empty')}</div>}

      {projects !== null && projects.length > 0 && (
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
