import { STEP_ORDER, type StepKey } from '../state/steps'

export function ProgressDots({ steps }: { steps: Record<StepKey, boolean> }) {
  return (
    <div className="progress-dots">
      {STEP_ORDER.map((s) => (
        <span key={s} className={`progress-dot ${steps[s] ? 'done' : ''}`} title={s} />
      ))}
    </div>
  )
}
