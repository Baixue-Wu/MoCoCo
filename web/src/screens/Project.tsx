import { NavLink, Route, Routes, useParams } from 'react-router-dom'
import { useI18n } from '../i18n'
import { ProjectProvider, useProject } from '../state/ProjectContext'
import { STEP_ORDER, allSteps, type StepKey } from '../state/steps'
import { Spinner } from '../components/Spinner'
import { useToast } from '../components/Toast'
import { SetupStep } from './steps/Setup'
import { ScriptStep } from './steps/Script'
import { ShotsStep } from './steps/Shots'
import { CutStep } from './steps/Cut'
import { VoiceStep } from './steps/Voice'
import { ExportStep } from './steps/Export'

const STEP_PATH: Record<StepKey, string> = {
  setup: '',
  script: 'script',
  shots: 'shots',
  cut: 'cut',
  voice: 'voice',
  export: 'export',
}

function WizardNav() {
  const { t } = useI18n()
  const { detail } = useProject()
  const steps = detail ? allSteps(detail.status) : null
  return (
    <nav className="wizard-nav">
      {STEP_ORDER.map((s) => (
        <NavLink key={s} to={STEP_PATH[s] || '.'} end={s === 'setup'} className={({ isActive }) => (isActive ? 'active' : '')}>
          <span>{t(`step.${s}`)}</span>
          <span className={`dot ${steps?.[s] ? 'done' : ''}`} />
        </NavLink>
      ))}
    </nav>
  )
}

function RunAllRemaining() {
  const { t } = useI18n()
  const { runStage, isBusy } = useProject()
  const { showError } = useToast()
  return (
    <button
      className="btn btn-primary"
      disabled={isBusy}
      onClick={() => {
        runStage('run', {}).catch(showError)
      }}
    >
      {t('wizard.run_all')}
    </button>
  )
}

function WizardBody() {
  const { detail, loading } = useProject()

  if (loading && !detail) {
    return (
      <div className="center-msg">
        <Spinner />
      </div>
    )
  }
  if (!detail) {
    return <div className="center-msg">404</div>
  }

  return (
    <div>
      <div className="row-between" style={{ marginBottom: 18 }}>
        <div>
          <h1 style={{ marginBottom: 2 }}>{detail.settings.title}</h1>
          <span className="badge badge-accent">{detail.settings.style}</span>
        </div>
        <RunAllRemaining />
      </div>
      <div className="wizard">
        <WizardNav />
        <div>
          <Routes>
            <Route index element={<SetupStep />} />
            <Route path="script" element={<ScriptStep />} />
            <Route path="shots" element={<ShotsStep />} />
            <Route path="cut" element={<CutStep />} />
            <Route path="voice" element={<VoiceStep />} />
            <Route path="export" element={<ExportStep />} />
          </Routes>
        </div>
      </div>
    </div>
  )
}

export function ProjectScreen() {
  const { slug } = useParams<{ slug: string }>()
  if (!slug) return null
  return (
    <ProjectProvider slug={slug}>
      <WizardBody />
    </ProjectProvider>
  )
}
