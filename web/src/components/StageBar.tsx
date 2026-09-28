import { useI18n } from '../i18n'
import { useProject } from '../state/ProjectContext'
import { Spinner } from './Spinner'
import type { StageRequest } from '../api'

export function StageBar({
  stage,
  done,
  extra,
  onDone,
  confirmRedo,
}: {
  stage: string
  done: boolean
  extra?: StageRequest
  onDone?: () => void
  confirmRedo?: string
}) {
  const { t } = useI18n()
  const { jobsByStage, isBusy, runStage } = useProject()
  const job = jobsByStage[stage]
  const runningThis = job?.status === 'running'
  const disableActions = isBusy && !runningThis

  const go = async (force: boolean) => {
    if (force && confirmRedo && !window.confirm(confirmRedo)) return
    try {
      await runStage(stage, { ...extra, force })
      onDone?.()
    } catch {
      /* error already toasted / shown in error box below */
    }
  }

  return (
    <div className="card stage-bar">
      <div className="hstack">
        {runningThis ? (
          <span className="hstack gap-sm">
            <Spinner />
            {t('wizard.running', { stage })}
          </span>
        ) : (
          <span className={`badge ${done ? 'badge-ok' : ''}`}>{done ? t('wizard.done') : t('wizard.not_done')}</span>
        )}
      </div>
      <div className="actions">
        {!done && (
          <button className="btn btn-primary" disabled={disableActions || runningThis} onClick={() => go(false)}>
            {t('wizard.run_step')}
          </button>
        )}
        {done && (
          <button className="btn" disabled={disableActions || runningThis} onClick={() => go(true)}>
            {t('wizard.redo_step')}
          </button>
        )}
      </div>
      {job?.status === 'failed' && (
        <div className="error-box" style={{ width: '100%' }}>
          {job.error}
        </div>
      )}
    </div>
  )
}
