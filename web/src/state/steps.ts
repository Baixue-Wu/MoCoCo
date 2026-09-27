import type { Status } from '../api'

export type StepKey = 'setup' | 'script' | 'shots' | 'cut' | 'voice' | 'export'

export const STEP_ORDER: StepKey[] = ['setup', 'script', 'shots', 'cut', 'voice', 'export']

function allTrue(dict: Record<string, boolean>): boolean {
  const vals = Object.values(dict)
  if (vals.length === 0) return false
  return vals.every(Boolean)
}

export function stepDone(step: StepKey, status: Status): boolean {
  switch (step) {
    case 'setup':
      return status.ingest
    case 'script':
      return status.segments
    case 'shots':
      return status.retrieve
    case 'cut':
      return status.cut
    case 'voice':
      return allTrue(status.voice)
    case 'export':
      return allTrue(status.render)
  }
}

export function allSteps(status: Status): Record<StepKey, boolean> {
  const out = {} as Record<StepKey, boolean>
  for (const s of STEP_ORDER) out[s] = stepDone(s, status)
  return out
}
