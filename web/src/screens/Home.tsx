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
      <section className="home-hero">
        <div className="home-hero-copy">
          <p className="home-eyebrow">{t('home.eyebrow')}</p>
          <h1>{t('home.hero_title')}</h1>
          <p className="home-lead">{t('home.hero_description')}</p>
          <div className="home-actions">
            <button className="btn btn-primary" onClick={() => document.getElementById('home-examples')?.scrollIntoView({ behavior: 'smooth' })}>{t('home.explore')}</button>
            <button className="btn" onClick={() => setShowForm(true)}>{t(publicMode ? 'home.import_film' : 'home.new_project')}</button>
          </div>
        </div>
        <Link to="/examples/sintel-analysis/export" className="home-hero-film">
          <img src={`${import.meta.env.BASE_URL}examples/sintel-analysis/frame-196.jpg`} alt={t('home.hero_caption')} />
          <div><span className="home-play" aria-hidden="true">▶</span><p>{t('home.hero_caption')}</p><strong>{t('home.hero_watch')}</strong></div>
        </Link>
      </section>

      <section className="home-section" aria-labelledby="home-features">
        <h2 id="home-features">{t('home.features_title')}</h2>
        <div className="home-features">{['script', 'shots', 'evidence'].map((item, i) => <article className="card" key={item}><span className="home-number">0{i + 1}</span><h3>{t(`home.feature_${item}_title`)}</h3><p>{t(`home.feature_${item}_body`)}</p></article>)}</div>
      </section>

      <section className="home-section" aria-labelledby="home-workflow">
        <h2 id="home-workflow">{t('home.workflow_title')}</h2><p className="muted">{t('home.workflow_hint')}</p>
        <ol className="home-flow">{[['setup', ''], ['script', 'evidence'], ['shots', 'shots'], ['cut', 'cut'], ['voice', 'voice'], ['export', 'export']].map(([step, path], i) => <li key={step}><Link to={`/examples/sintel-analysis/${path}`}><span className="home-number">{String(i + 1).padStart(2, '0')}</span><strong>{t(`home.flow_${step}`)}</strong><span>{t(`home.flow_${step}_detail`)}</span></Link></li>)}</ol>
      </section>

      <section className="home-section" id="home-examples" aria-labelledby="home-examples-title">
        <h2 id="home-examples-title">{t('home.examples_title')}</h2><p className="muted">{t('home.examples_hint')}</p>
        <div className="home-examples">
          <Link to="/examples/sherlock-jr" className="card project-card example-project-card">
            <img src="https://baixue-wu.github.io/MoCoCo/assets/sherlock-jr-poster.jpg" alt="Sherlock Jr." />
            <span className="badge badge-accent">{t('home.recap_title')}</span>
            <h2>{t('example.project_title')}</h2><p>{t('home.recap_body')}</p>
            <ProgressDots steps={{ setup: true, script: true, shots: true, cut: true, voice: true, export: true }} />
            <span className="small muted">{t('example.project_hint')}</span><strong>{t('home.enter_example')}</strong>
          </Link>
          <Link to="/examples/sintel-analysis" className="card project-card example-project-card">
            <img src={`${import.meta.env.BASE_URL}examples/sintel-analysis/frame-669.jpg`} alt="Sintel" />
            <span className="badge badge-accent">{t('home.analysis_title')}</span>
            <h2>Sintel · {t('analysis.title')}</h2><p>{t('home.analysis_body')}</p>
            <span className="small muted">{t('analysis.hint')}</span><strong>{t('home.enter_example')}</strong>
          </Link>
        </div>
      </section>

      <section className="home-section home-projects" aria-labelledby="home-projects-title">
        <div className="row-between"><div><h2 id="home-projects-title">{t('home.projects_title')}</h2><p className="muted">{t('home.projects_hint')}</p></div><button className="btn btn-primary" onClick={() => setShowForm(true)}>{t(publicMode ? 'home.import_film' : 'home.new_project')}</button></div>
      {(publicMode ? browserProjects === null : projects === null) && (
        <div className="center-msg">
          <Spinner />
        </div>
      )}

      {(publicMode ? browserProjects !== null : projects !== null) && (
        <div className="grid-cards">
          {publicMode && browserProjects?.map((p) => (
            <Link key={p.slug} to={`/p/${p.slug}`} className="card project-card">
              <div className="row-between">
                <h2 style={{ margin: 0 }}>{p.title}</h2>
                <span className="badge badge-accent">{t('browser.local_badge')}</span>
              </div>
              <span className="small muted">{p.film_name}</span>
              <span className="small muted">{new Date(p.created * 1000).toLocaleDateString()}</span>
            </Link>
          ))}
          {!publicMode && projects?.map((p) => (
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

      {(publicMode ? browserProjects?.length === 0 : projects?.length === 0) && <p className="home-empty">{t('home.projects_empty')}</p>}
      </section>

      <footer className="home-footer small muted">
        <span>MoCoCo · Baixue Wu · <a href="https://github.com/Baixue-Wu/MoCoCo">GitHub</a></span>
        <span>© copyright Blender Foundation | <a href="https://durian.blender.org/sharing">www.sintel.org</a> · <a href="https://creativecommons.org/licenses/by/3.0/">CC BY 3.0</a></span>
      </footer>

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
