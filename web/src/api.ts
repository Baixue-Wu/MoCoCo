// Typed fetch wrapper. One function per endpoint the UI uses.
// Mirrors mococo/server/app.py; see web/API-REQUESTS.md for anything the API is missing.

export class ApiError extends Error {
  status: number
  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
  }
}

async function req<T>(method: string, path: string, body?: unknown, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body !== undefined && !(body instanceof FormData) ? { 'Content-Type': 'application/json' } : undefined,
    body: body instanceof FormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
    ...init,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const j = await res.json()
      detail = j.detail ?? detail
    } catch {
      /* not json */
    }
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  const text = await res.text()
  return (text ? JSON.parse(text) : undefined) as T
}

const get = <T,>(path: string) => req<T>('GET', path)
const post = <T,>(path: string, body?: unknown) => req<T>('POST', path, body)
const put = <T,>(path: string, body?: unknown) => req<T>('PUT', path, body)
const del = <T,>(path: string) => req<T>('DELETE', path)

// ---- shared types ----

export type Lang = 'zh' | 'en'
export type Style = 'recap' | 'analysis'

export interface Voice {
  zh: string
  en: string
  rate: string
}

export interface Settings {
  title: string
  film: string
  style: Style
  script_langs: Lang[]
  subtitle_langs: Lang[]
  subtitle_position?: 'bottom' | 'top'
  voice_langs: Lang[]
  target_minutes: number
  brief: string
  voice: Voice
  created: number
}

export interface Status {
  ingest: boolean
  ingest_steps: { shots: boolean; transcript: boolean; captions: boolean; index: boolean }
  script: Record<string, boolean>
  segments: boolean
  retrieve: boolean
  cut: boolean
  voice: Record<string, boolean>
  uploads: Record<string, boolean>
  render: Record<string, boolean>
}

export interface ProjectSummary {
  slug: string
  title: string
  style: Style
  created: number
  status: Status
}

export interface FilmInfo {
  duration: number
  width: number
  height: number
  fps: number
  has_audio: boolean
}

export interface Job {
  id: string
  project: string
  stage: string
  status: 'running' | 'done' | 'failed'
  started: number
  finished: number | null
  error: string | null
  result: unknown
}

export interface ProjectDetail {
  slug: string
  settings: Settings
  status: Status
  film: FilmInfo | null
  jobs: Job[]
}

export interface StyleInfo {
  label: { en: string; zh: string }
  guidance: string
}

export interface NewProjectBody {
  slug: string
  title?: string
  style: Style
  script_langs: Lang[]
  subtitle_langs?: Lang[]
  voice_langs?: Lang[]
  target_minutes: number
  brief: string
}

export interface StageRequest {
  force?: boolean
  lang?: string | null
  top?: number
  whisper?: string
}

// ---- shot / caption / script / retrieval / cut / voice file shapes ----

export interface Shot {
  id: string
  start: number
  end: number
  duration: number
  frame: string
}

export interface Transcript {
  language: string
  segments: { start: number; end: number; text: string }[]
}

export interface Caption {
  description_en: string
  description_zh: string
  mood: string
  characters: string[]
  setting: string
  tags: string[]
  dialogue: string
}

export type Captions = Record<string, Caption>

export interface Unit {
  id: string
  text: Record<string, string>
  intent: string
  mood: string
  visual_query_en: string
  keywords: string[]
  needs_context: boolean
  context_query: string
}

export interface Segments {
  primary_lang: Lang
  units: Unit[]
}

export interface CandidateShot {
  shot_id: string
  score: number
  why: string
  why_zh?: string
  similarity: number
}

export interface ExternalRef {
  image_url: string
  source_url: string
  caption: string
  file: string
}

export interface UnitCandidates {
  unit_id: string
  shots: CandidateShot[]
  external: ExternalRef[]
  chosen: string[]
}

export interface Candidates {
  units: UnitCandidates[]
}

export interface ShotClip {
  kind?: 'shot'
  shot_id: string
  in: number
  out: number
  seconds: number
  why: string
  why_zh?: string
  freeze?: number
}

export interface ImageClip {
  kind: 'image'
  file: string
  caption: string
  seconds: number
}

export type Clip = ShotClip | ImageClip

export function isImageClip(c: Clip): c is ImageClip {
  return c.kind === 'image'
}

/** Chinese "why" when the UI is in Chinese and one was given, else the English/default one. */
export function pickWhy(item: { why: string; why_zh?: string }, uiLang: string): string {
  return uiLang === 'zh' && item.why_zh ? item.why_zh : item.why
}

export interface TimelineUnit {
  id: string
  estimated_seconds: number
  clips: Clip[]
}

export interface Timeline {
  style: Style
  units: TimelineUnit[]
}

export interface TimingUnit {
  id: string
  start: number
  end: number
  words: { start: number; end: number; word: string }[]
}

export interface Timing {
  lang: Lang
  voice: string
  source: 'tts' | 'upload'
  units: TimingUnit[]
}

export interface EventRecord {
  t: number
  kind: string
  [key: string]: unknown
}

// ---- catalogue ----

export const createProjectFromFile = (settings: NewProjectBody, file: File, onProgress: (percent: number) => void) =>
  new Promise<{ slug: string; settings: Settings; status: Status }>((resolve, reject) => {
    const request = new XMLHttpRequest()
    request.open('POST', '/api/projects/upload')
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100))
    }
    request.onerror = () => reject(new Error('Movie upload failed'))
    request.onload = () => {
      let result: { slug: string; settings: Settings; status: Status } | { detail?: string }
      try {
        result = JSON.parse(request.responseText)
      } catch {
        reject(new ApiError(request.status, request.statusText))
        return
      }
      if (request.status >= 200 && request.status < 300) resolve(result as { slug: string; settings: Settings; status: Status })
      else reject(new ApiError(request.status, (result as { detail?: string }).detail ?? request.statusText))
    }
    const body = new FormData()
    body.append('settings', JSON.stringify(settings))
    body.append('file', file)
    request.send(body)
  })
export const listStyles = () => get<Record<Style, StyleInfo>>('/styles')
export const listVoices = (lang: string) => get<string[]>(`/voices?lang=${encodeURIComponent(lang)}`)

// ---- projects ----

export const listProjects = () => get<ProjectSummary[]>('/projects')
export const getProject = (slug: string) => get<ProjectDetail>(`/projects/${slug}`)
export const putSettings = (slug: string, body: Settings) => put<Settings>(`/projects/${slug}/settings`, body)
export const deleteProject = (slug: string) => del<{ deleted: string }>(`/projects/${slug}`)

// ---- files ----

export const getFile = <T,>(slug: string, name: string) => get<T>(`/projects/${slug}/files/${name}`)
export const putFile = (slug: string, name: string, body: unknown) => put<{ ok: true }>(`/projects/${slug}/files/${name}`, body)

export const getScript = (slug: string, lang: Lang) => getFile<{ text: string }>(slug, `script.${lang}`)
export const putScript = (slug: string, lang: Lang, text: string) => putFile(slug, `script.${lang}`, { text })
export const getShots = (slug: string) => getFile<Shot[]>(slug, 'shots')
export const getTranscript = (slug: string) => getFile<Transcript>(slug, 'transcript')
export const getCaptions = (slug: string) => getFile<Captions>(slug, 'captions')
export const getSegments = (slug: string) => getFile<Segments>(slug, 'segments')
export const getCandidates = (slug: string) => getFile<Candidates>(slug, 'candidates')
export const putCandidates = (slug: string, body: Candidates) => putFile(slug, 'candidates', body)
export const getTimeline = (slug: string) => getFile<Timeline>(slug, 'timeline')
export const putTimeline = (slug: string, body: Timeline) => putFile(slug, 'timeline', body)
export const getTiming = (slug: string, lang: Lang) => getFile<Timing>(slug, `timing.${lang}`)
export const getEvents = (slug: string) => getFile<EventRecord[]>(slug, 'events')

// ---- stages ----

export const runStage = (slug: string, stage: string, body: StageRequest = {}) =>
  post<Job>(`/projects/${slug}/stages/${stage}`, body)
export const getJob = (id: string) => get<Job>(`/jobs/${id}`)

// ---- events (interaction trace) ----

export const postEvent = (slug: string, body: Record<string, unknown>) => post<{ ok: true }>(`/projects/${slug}/events`, body)

// ---- media urls (used directly as src/href) ----

export const mediaFrame = (slug: string, shotId: string) => `/api/projects/${slug}/media/frame/${shotId}`
export const mediaExternal = (slug: string, name: string) => `/api/projects/${slug}/media/external/${name}`
export const mediaPreview = (slug: string, shotId: string) => `/api/projects/${slug}/media/preview/${shotId}`
export const mediaNarration = (slug: string, lang: string) => `/api/projects/${slug}/media/narration/${lang}`
export const mediaOutput = (slug: string, lang: string) => `/api/projects/${slug}/media/output/${lang}`

export const uploadNarration = (slug: string, lang: string, file: File) => {
  const fd = new FormData()
  fd.append('file', file)
  return post<{ ok: true; path: string }>(`/projects/${slug}/upload/narration/${lang}`, fd)
}
export const deleteUploadedNarration = (slug: string, lang: string) => del<{ ok: true }>(`/projects/${slug}/upload/narration/${lang}`)
