import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { deleteBrowserProject, getBrowserProject, type BrowserProject } from '../browserProjects'
import { useI18n } from '../i18n'
import { useToast } from '../components/Toast'

export function BrowserProjectScreen() {
  const { slug } = useParams<{ slug: string }>()
  const { t } = useI18n()
  const { showError } = useToast()
  const navigate = useNavigate()
  const [project, setProject] = useState<BrowserProject | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!slug) return
    let active = true
    let url: string | null = null
    getBrowserProject(slug).then((p) => {
      if (!active || !p) return
      url = URL.createObjectURL(p.film)
      setProject(p)
      setVideoUrl(url)
    }).catch(showError)
    return () => {
      active = false
      if (url) URL.revokeObjectURL(url)
    }
  }, [slug, showError])

  if (!project) return <div className="center-msg">{t('browser.loading_or_missing')}</div>

  return (
    <div className="example-page">
      <Link to="/" className="small">← {t('common.back')}</Link>
      <div className="row-between" style={{ margin: '22px 0' }}>
        <div>
          <h1>{project.title}</h1>
          <span className="badge badge-accent">{t('browser.local_badge')}</span>
        </div>
        <button className="btn btn-danger" onClick={async () => {
          if (!window.confirm(t('browser.delete_confirm'))) return
          try {
            await deleteBrowserProject(project.slug)
            navigate('/')
          } catch (error) { showError(error) }
        }}>{t('common.delete')}</button>
      </div>
      <div className="card section">
        <h2>{t('browser.film')}</h2>
        <p className="muted">{project.film_name} · {(project.film_size / 1e6).toFixed(1)} MB</p>
        {videoUrl && <video controls src={videoUrl} />}
        <p className="small muted" style={{ marginTop: 12 }}>{t('browser.storage_note')}</p>
      </div>
      <div className="card section">
        <h2>{t('browser.project_settings')}</h2>
        <p>{t('newp.style')}: {t(`browser.style.${project.style}`)} · {t('newp.target_minutes')}: {project.target_minutes}</p>
        {project.brief && <p>{project.brief}</p>}
      </div>
      <div className="card section">
        <h2>{t('browser.next_steps')}</h2>
        <p>{t('browser.processing_notice')}</p>
        <Link to={project.style === "analysis" ? "/examples/sintel-analysis" : "/examples/sherlock-jr"}>{t('example.browse')} →</Link>
      </div>
    </div>
  )
}
