import { useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Route, Routes } from 'react-router-dom'
import type { Candidates, Captions, Segments, Shot, Timeline, TimingUnit } from '../api'
import { isImageClip, pickWhy } from '../api'
import { Modal } from '../components/Modal'
import { Spinner } from '../components/Spinner'
import { useI18n } from '../i18n'
import { STEP_ORDER, type StepKey } from '../state/steps'

const base = `${import.meta.env.BASE_URL}examples/sherlock-jr`
const stepPath: Record<StepKey, string> = {
  setup: '', script: 'script', shots: 'shots', cut: 'cut', voice: 'voice', export: 'export',
}

interface ExampleData {
  title: string
  style: string
  target_minutes: number
  brief: string
  film: { duration: number; width: number; height: number; fps: number; has_audio: boolean }
  shot_count: number
  caption_count: number
  script: string
  segments: Segments
  candidates: Candidates
  timeline: Timeline
  timing: { voice: string; units: TimingUnit[] }
  shots: Shot[]
  captions: Captions
  source_url: string
  result_url: string
  full_result_url: string
}

function clock(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${Math.floor(seconds % 60).toString().padStart(2, '0')}`
}

export function SherlockJrExample() {
  const { t, lang } = useI18n()
  const [data, setData] = useState<ExampleData | null>(null)
  const [error, setError] = useState('')
  const [frameId, setFrameId] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetch(`${base}/project.json`, { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error(`${response.status} ${response.statusText}`)
        return response.json() as Promise<ExampleData>
      })
      .then(setData)
      .catch((cause: unknown) => { if (!controller.signal.aborted) setError(String(cause)) })
    return () => controller.abort()
  }, [])

  const byId = useMemo(() => new Map(data?.shots.map((shot) => [shot.id, shot]) ?? []), [data])
  const candidateByUnit = useMemo(() => new Map(data?.candidates.units.map((unit) => [unit.unit_id, unit]) ?? []), [data])
  const timelineByUnit = useMemo(() => new Map(data?.timeline.units.map((unit) => [unit.id, unit]) ?? []), [data])
  const frame = (id: string) => `${base}/frames/${id}.jpg`
  const caption = (id: string) => {
    const item = data?.captions[id]
    return lang === 'zh' ? item?.description_zh || item?.description_en : item?.description_en || item?.description_zh
  }

  if (error) return <div className="center-msg">{t('example.load_error')}: {error}</div>
  if (!data) return <div className="center-msg"><Spinner /></div>

  const setup = (
    <div>
      <div className="card section">
        <h2>{t('setup.settings')}</h2>
        <div className="kv-grid">
          <div><div className="k">{t('newp.style')}</div>{t(`browser.style.${data.style}`)}</div>
          <div><div className="k">{t('newp.script_langs')}</div>{t('newp.lang.zh')}</div>
          <div><div className="k">{t('newp.target_minutes')}</div>{data.target_minutes}</div>
        </div>
        <p style={{ marginTop: 16 }}>{data.brief}</p>
      </div>
      <div className="card section">
        <h2>{t('setup.film_info')}</h2>
        <div className="kv-grid">
          <div><div className="k">{t('setup.film_duration')}</div>{clock(data.film.duration)}</div>
          <div><div className="k">{t('setup.film_resolution')}</div>{data.film.width}×{data.film.height}</div>
          <div><div className="k">{t('setup.film_fps')}</div>{data.film.fps.toFixed(2)}</div>
          <div><div className="k">{t('setup.shots_heading')}</div>{data.shot_count}</div>
        </div>
        <p className="small muted" style={{ marginTop: 14 }}>{t('example.captions_count', { n: data.caption_count })}</p>
        <a href={data.source_url}>{t('example.download_source')}</a>
      </div>
      <div className="card section">
        <h2>{t('example.keyframes')}</h2>
        <p className="muted">{t('example.keyframes_hint', { n: data.shots.length })}</p>
        <div className="shot-grid">
          {data.shots.map((shot) => (
            <button type="button" key={shot.id} className="shot-thumb example-frame-button" onClick={() => setFrameId(shot.id)} title={caption(shot.id)}>
              <img src={frame(shot.id)} loading="lazy" alt={caption(shot.id) || shot.id} />
              <span className="shot-id">{shot.id} · {clock(shot.start)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )

  const script = (
    <div>
      <div className="card section">
        <div className="row-between"><h2>{t('example.script')}</h2><span className="badge">{data.segments.units.length} {t('example.units')}</span></div>
        <p className="muted">{t('example.script_hint')}</p>
        {data.script.split(/\n\s*\n/).map((paragraph, index) => (
          <div className="example-script-paragraph" key={index}>
            <span className="badge badge-accent">u{String(index + 1).padStart(3, '0')}</span>
            <p>{paragraph}</p>
          </div>
        ))}
      </div>
      <h2>{t('script.units_heading')}</h2>
      <div className="grid-cards">
        {data.segments.units.map((unit) => (
          <div key={unit.id} className="card section">
            <div className="row-between"><span className="badge badge-accent">{unit.id}</span><span className="badge">{unit.intent}</span></div>
            <p style={{ marginTop: 12 }}>{unit.text.zh}</p>
            <p className="small muted">{t('setup.mood')}: {unit.mood}</p>
            <p className="small muted">{t('script.visual_query')}: {unit.visual_query_en}</p>
            <p className="small muted">{t('script.keywords')}: {unit.keywords.join(', ')}</p>
          </div>
        ))}
      </div>
    </div>
  )

  const shots = (
    <div>
      <p className="muted">{t('example.shots_hint')}</p>
      {data.segments.units.map((unit) => {
        const candidates = candidateByUnit.get(unit.id)
        const used = new Set(timelineByUnit.get(unit.id)?.clips.filter((clip) => !isImageClip(clip)).map((clip) => !isImageClip(clip) ? clip.shot_id : '') ?? [])
        return (
          <div key={unit.id} className="card unit-row">
            <div className="row-between"><span className="badge badge-accent">{unit.id}</span><span className="badge">{unit.mood}</span></div>
            <p style={{ marginTop: 10 }}>{unit.text.zh}</p>
            <div className="unit-strip">
              {candidates?.shots.map((candidate) => {
                const selected = candidates.chosen.includes(candidate.shot_id)
                const shot = byId.get(candidate.shot_id)
                return (
                  <div className="cand-thumb example-candidate" key={candidate.shot_id}>
                    <button type="button" className={`shot-thumb example-frame-button ${selected ? 'chosen' : ''}`} onClick={() => setFrameId(candidate.shot_id)}>
                      <img src={frame(candidate.shot_id)} loading="lazy" alt={caption(candidate.shot_id) || candidate.shot_id} />
                      <span className="shot-id">{candidate.shot_id}</span>
                    </button>
                    <div className="example-candidate-badges">
                      {selected && <span className="badge badge-accent">{t('example.initial_choice')}</span>}
                      {used.has(candidate.shot_id) && <span className="badge badge-ok">{t('example.used_in_cut')}</span>}
                    </div>
                    <div className="cand-meta">{t('shots.score', { v: candidate.score.toFixed(0) })} · {shot && clock(shot.start)}</div>
                    <p className="small">{caption(candidate.shot_id)}</p>
                    <p className="cand-meta">{pickWhy(candidate, lang)}</p>
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )

  const cut = (
    <div>
      <p className="muted">{t('example.cut_hint')}</p>
      {data.timeline.units.map((unit) => {
        const segment = data.segments.units.find((item) => item.id === unit.id)
        return (
          <div key={unit.id} className="card unit-row">
            <div className="row-between"><span className="badge badge-accent">{unit.id}</span><span className="small muted">{unit.clips.length} {t('example.clips')} · {unit.estimated_seconds.toFixed(1)}s</span></div>
            <p style={{ marginTop: 10 }}>{segment?.text.zh}</p>
            <div className="clip-strip">
              {unit.clips.map((clip, index) => isImageClip(clip) ? null : (
                <button type="button" className="clip-block example-clip" key={`${unit.id}-${index}`} onClick={() => setFrameId(clip.shot_id)}>
                  <img src={frame(clip.shot_id)} loading="lazy" alt={caption(clip.shot_id) || clip.shot_id} />
                  <span className="clip-info"><strong>{index + 1}. {clip.shot_id}</strong><span>{clip.in.toFixed(1)}–{clip.out.toFixed(1)}s</span><span>{clip.seconds.toFixed(1)}s</span></span>
                </button>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )

  const voice = (
    <div className="card section">
      <h2>{t('voice.heading')}</h2>
      <p>{t('voice.voice_name')}: {data.timing.voice}</p>
      <audio controls preload="metadata" src={`${base}/narration.zh.mp3`} />
      <h3 style={{ marginTop: 20 }}>{t('voice.timing_heading')}</h3>
      <table className="timing-table"><thead><tr><th>{t('voice.timing_unit')}</th><th>{t('voice.timing_start')}</th><th>{t('voice.timing_end')}</th></tr></thead>
        <tbody>{data.timing.units.map((unit) => <tr key={unit.id}><td>{unit.id}</td><td>{unit.start.toFixed(2)}s</td><td>{unit.end.toFixed(2)}s</td></tr>)}</tbody>
      </table>
    </div>
  )

  const output = (
    <div className="card section">
      <h2>{t('export.heading')}</h2>
      <video controls preload="metadata" poster="https://baixue-wu.github.io/MoCoCo/assets/sherlock-jr-poster.jpg" src={data.result_url} />
      <div className="example-video-links"><a href={data.full_result_url}>{t('example.download_result')}</a><a href={data.source_url}>{t('example.download_source')}</a></div>
      <p className="small muted">{t('example.source_note')} <a href="https://commons.wikimedia.org/wiki/File:Sherlock_Jr.(1924).webm">Wikimedia Commons</a></p>
    </div>
  )

  return (
    <div>
      <Link to="/" className="small">← {t('common.back')}</Link>
      <div className="row-between example-project-heading">
        <div><h1>{data.title}</h1><span className="badge badge-accent">{t('example.read_only')}</span></div>
        <Link to="/" className="btn">{t('example.try')}</Link>
      </div>
      <p className="muted example-project-note">{t('example.project_intro')}</p>
      <div className="wizard">
        <nav className="wizard-nav" aria-label={t('example.workflow')}>
          {STEP_ORDER.map((step) => <NavLink key={step} to={stepPath[step] || '.'} end={step === 'setup'} className={({ isActive }) => isActive ? 'active' : ''}><span>{t(`step.${step}`)}</span><span className="dot done" /></NavLink>)}
        </nav>
        <div>
          <Routes>
            <Route index element={setup} />
            <Route path="script" element={script} />
            <Route path="shots" element={shots} />
            <Route path="cut" element={cut} />
            <Route path="voice" element={voice} />
            <Route path="export" element={output} />
          </Routes>
        </div>
      </div>
      {frameId && (
        <Modal onClose={() => setFrameId(null)}>
          <h2>{frameId} · {clock(byId.get(frameId)?.start ?? 0)}</h2>
          <img className="example-frame-large" src={frame(frameId)} alt={caption(frameId) || frameId} />
          <p>{caption(frameId)}</p>
          {data.captions[frameId]?.tags.length > 0 && <p className="small muted">{t('setup.tags')}: {data.captions[frameId].tags.join(', ')}</p>}
        </Modal>
      )}
    </div>
  )
}
