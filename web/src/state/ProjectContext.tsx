import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import * as api from '../api'
import { ApiError } from '../api'
import { useToast } from '../components/Toast'

const POLL_MS = 1500

interface ProjectContextValue {
  slug: string
  detail: api.ProjectDetail | null
  loading: boolean
  refresh: () => Promise<void>
  jobsByStage: Record<string, api.Job>
  isBusy: boolean
  runStage: (stage: string, body?: api.StageRequest) => Promise<api.Job>
}

const ProjectContext = createContext<ProjectContextValue | null>(null)

export function ProjectProvider({ slug, children }: { slug: string; children: ReactNode }) {
  const [detail, setDetail] = useState<api.ProjectDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [jobsByStage, setJobsByStage] = useState<Record<string, api.Job>>({})
  const { showError } = useToast()
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  const refresh = useCallback(async () => {
    try {
      const d = await api.getProject(slug)
      if (mounted.current) setDetail(d)
    } catch (e) {
      showError(e)
    } finally {
      if (mounted.current) setLoading(false)
    }
  }, [slug, showError])

  useEffect(() => {
    setLoading(true)
    void refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug])

  const isBusy = Object.values(jobsByStage).some((j) => j.status === 'running')

  const runStage = useCallback(
    async (stage: string, body: api.StageRequest = {}) => {
      let job: api.Job
      try {
        job = await api.runStage(slug, stage, body)
      } catch (e) {
        if (e instanceof ApiError) showError(e.message)
        else showError(e)
        throw e
      }
      setJobsByStage((cur) => ({ ...cur, [stage]: job }))
      // poll until done or failed
      for (;;) {
        await new Promise((r) => setTimeout(r, POLL_MS))
        let latest: api.Job
        try {
          latest = await api.getJob(job.id)
        } catch {
          continue
        }
        setJobsByStage((cur) => ({ ...cur, [stage]: latest }))
        if (latest.status !== 'running') {
          await refresh()
          if (latest.status === 'failed') throw new Error(latest.error ?? 'stage failed')
          return latest
        }
      }
    },
    [slug, refresh, showError],
  )

  const value = useMemo(
    () => ({ slug, detail, loading, refresh, jobsByStage, isBusy, runStage }),
    [slug, detail, loading, refresh, jobsByStage, isBusy, runStage],
  )

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>
}

export function useProject(): ProjectContextValue {
  const ctx = useContext(ProjectContext)
  if (!ctx) throw new Error('useProject must be used within ProjectProvider')
  return ctx
}
