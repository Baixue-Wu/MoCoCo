import { useEffect, useRef, useState } from 'react'
import { Link, Navigate, Route, Routes } from 'react-router-dom'
import type { ImageCandidate, KnowledgeAnswer, KnowledgeChunk, KnowledgeSource, Segments, Shot, TimingUnit } from '../api'
import { ExampleWorkflow } from '../components/ExampleWorkflow'
import { Modal } from '../components/Modal'
import { Spinner } from '../components/Spinner'
import { useI18n } from '../i18n'

interface RenderedClip {
  kind?: string; shot_id?: string; file?: string; caption?: string
  in?: number; out?: number; render_start: number; render_end: number; render_seconds: number
  attribution?: ImageCandidate & { changes: string }
}
interface Study {
  title: string
  movie: { title: string; author: string; duration: number; url: string; chapters: { title: string; start: number; end: number }[]; script: string }
  saved_run?: KnowledgeAnswer
  chunks: KnowledgeChunk[]
  source_url: string; license_url: string; attribution: string; changes: string
  workflow: {
    film: { duration: number; width: number; height: number; fps: number }
    segments: Segments; shots: Shot[]; timeline: { id: string; clips: RenderedClip[] }[]
    sources: KnowledgeSource[]
    evidence: { unit: string; source_ids: string[]; retrieved: KnowledgeChunk[] }[]
    timing: { voice: string; source: string; units: TimingUnit[] }
    narration_url: string; subtitles: string; content_end: number
  }
}
const base = `${import.meta.env.BASE_URL}examples/sintel-analysis`
const root = '/examples/sintel-analysis'
const clock = (seconds: number) => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`

export function AnalysisExample() {
  const { lang } = useI18n()
  const label = (zh: string, en: string) => lang === 'zh' ? zh : en
  const [study, setStudy] = useState<Study | null>(null)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [frame, setFrame] = useState<{ file: string; title: string } | null>(null)
  const player = useRef<HTMLVideoElement>(null)
  useEffect(() => {
    const controller = new AbortController()
    fetch(`${base}/study.json`, { signal: controller.signal }).then(r => {
      if (!r.ok) throw new Error(`Could not load example: ${r.status}`)
      return r.json()
    }).then(data => {
      if (!data.workflow || !data.movie) throw new Error('Completed project data is missing')
      setStudy(data)
    }).catch(e => { if (!controller.signal.aborted) setError(String(e)) })
    return () => controller.abort()
  }, [])
  if (error) return <p role="alert">{error}</p>
  if (!study) return <div className="center-msg"><Spinner /></div>
  const w = study.workflow
  const steps = [
    { path: '', label: label('预处理', 'Preprocessing') },
    { path: 'evidence', label: label('资料检索 · RAG', 'Sources · RAG') },
    { path: 'script', label: label('成片文案', 'Script') },
    { path: 'shots', label: label('镜头与资料图', 'Shots and images') },
    { path: 'cut', label: label('剪辑时间线', 'Timeline') },
    { path: 'voice', label: label('配音与字幕', 'Voice and subtitles') },
    { path: 'export', label: label('成片', 'Output') },
  ]
  const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean)
  const hits = study.chunks.filter(c => !terms.length || terms.some(t => `${c.text} ${c.title}`.toLowerCase().includes(t)))
  const clipFrame = (clip: RenderedClip) => clip.kind === 'image' ? clip.file! : `frames/${clip.shot_id}.jpg`
  const clipTitle = (clip: RenderedClip) => clip.kind === 'image' ? label('外部概念图', 'External concept art') : `${label('原片', 'Source')} ${clock(clip.in!)}–${clock(clip.out!)}`
  const sourceLinks = (unit: string) => w.sources.filter(s => w.evidence.find(e => e.unit === unit)?.source_ids.includes(s.id)).map(s => <p key={s.id} className="small"><a href={s.url} target="_blank" rel="noreferrer">{s.title} ↗</a><span className="muted"> · {s.author}</span></p>)

  const setup = <>
    <section className="card section"><h2>{label('项目设置', 'Project settings')}</h2>
      <div className="kv-grid"><div><div className="k">{label('剪辑方式', 'Style')}</div>{label('深度解析', 'Deep analysis')}</div><div><div className="k">{label('解说语言', 'Language')}</div>{label('中文', 'Chinese')}</div><div><div className="k">{label('成片时长', 'Output length')}</div>{clock(study.movie.duration)}</div></div>
      <p>{study.movie.title}</p><p>{label('围绕照料与伤害的反转、画面关系和时间结构组织解说。按步骤查看这支视频使用的资料和制作结果。', 'Explore care, harm, visual relationships and time through the sources and decisions used in this finished film.')}</p>
      <Link className="btn" to={`${root}/export`}>{label('查看完整成片', 'Watch the finished film')}</Link>
    </section>
    <section className="card section"><h2>{label('原片与素材', 'Source film and material')}</h2>
      <div className="kv-grid"><div><div className="k">{label('原片时长', 'Film duration')}</div>{clock(w.film.duration)}</div><div><div className="k">{label('分辨率', 'Resolution')}</div>{w.film.width}×{w.film.height}</div><div><div className="k">FPS</div>{w.film.fps}</div><div><div className="k">{label('选用原片片段', 'Selected film excerpts')}</div>{w.shots.length}</div></div>
      <p><a href={study.source_url}>{label('下载官方原片 ZIP', 'Download official source ZIP')}</a> · <a href="https://durian.blender.org/sharing">{label('查看官方许可', 'Official rights')}</a></p>
      <p className="small muted">{study.attribution} · <a href={study.license_url}>CC BY 3.0</a> · {study.changes}</p>
    </section>
    <section className="card section"><h2>{label('选用片段的关键帧', 'Keyframes of selected excerpts')}</h2><p className="muted">{label('点击放大。时间对应原片；这些是按解析论点选用的片段，不是完整的自动镜头检测结果。', 'Click to enlarge. Times refer to the source film. These editorial selections are not a complete automatic shot-detection result.')}</p>
      <div className="shot-grid">{w.shots.map(s => <button className="shot-thumb example-frame-button" key={s.id} onClick={() => setFrame({ file: `frames/${s.id}.jpg`, title: `${s.id} · ${clock(s.start)}–${clock(s.end)}` })}><img src={`${base}/frames/${s.id}.jpg`} loading="lazy" alt={`${s.id} ${clock(s.start)}`} /><span className="shot-id">{s.id} · {clock(s.start)}</span></button>)}</div>
    </section>
  </>

  const evidence = <>
    <section className="card section"><h2>{label('参考资料与检索', 'Sources and retrieval')}</h2>
      <p className="muted">{label('查看影评摘记、官方许可和片内观察。这里筛选的是已保存的资料；实时检索与生成在本地编辑器使用。', 'Inspect saved review notes, licensing and film observations. This page filters recorded material; live retrieval and generation use the local editor.')}</p>
      <label>{label('筛选摘记（关键词，不调用模型）', 'Filter notes (keywords, no model)')}<input value={query} onChange={e => setQuery(e.target.value)} /></label>
      <div className="actions">{['悲剧', '表情', '许可', '时间'].map(q => <button className="btn" key={q} onClick={() => setQuery(q)}>{q}</button>)}<button className="btn" onClick={() => setQuery('')}>{label('全部', 'All')}</button></div>
      {!hits.length && <p role="status">{label('没有匹配的资料。', 'No matching source.')}</p>}
      {hits.map(c => <article key={c.id} className="card section"><h3><a href={c.url}>{c.title}</a></h3><p style={{ whiteSpace: 'pre-wrap' }}>{c.text}</p><p className="small muted">{c.author} · {c.rights}</p></article>)}
    </section>
    {study.saved_run && <section className="card section"><h2>{label('一次真实 RAG 运行记录', 'A recorded live RAG run')}</h2>
      <p>{study.saved_run.query}</p><p className="small muted">{label('这是已保存的模型建议，不等于最终解说词。成片文案经过编写和镜头核对；下一步可逐段查看实际采用的文字及来源。', 'These saved model suggestions are not the final script. The finished narration was written and checked against footage; inspect its actual paragraphs and sources in the next step.')}</p>
      {study.saved_run.claims.map((c, i) => <article key={i}><span className="badge">{c.kind === 'interpretation' ? label('解读建议', 'Interpretation') : label('来源陈述', 'Source statement')}</span><p>{c.text}</p><details><summary>{label('展开检索依据', 'Inspect retrieved evidence')}</summary>{c.citations.map(id => { const hit = study.saved_run!.retrieved.find(h => h.id === id); return hit && <blockquote key={id}><a href={hit.url}>{hit.title}</a><p>{hit.text}</p><small>{hit.id}</small></blockquote> })}</details></article>)}
      {study.saved_run.gaps.map((g, i) => <p className="muted" key={i}>{g}</p>)}
    </section>}
    <Link className="btn" to={`${root}/script`}>{label('查看成片文案', 'Read the finished script')}</Link>
  </>

  const script = <>
    <section className="card section"><div className="row-between"><h2>{label('实际成片解说词', 'Finished narration')}</h2><span className="badge">{w.segments.units.length} {label('段', 'units')}</span></div>
      <p className="muted">{label('下列文字与视频配音一致。展开每段可核查采用的资料及检索片段；引用支持解读过程，不代表已经证明导演意图。', 'These paragraphs match the narration. Expand each unit to inspect its sources and retrieved passages; citations do not prove director intent.')}</p>
      {w.segments.units.map(u => <article key={u.id} className="example-script-paragraph"><span className="badge badge-accent">{u.id}</span><h3>{u.intent}</h3><p>{u.text.zh}</p><details><summary>{label('查看本段资料依据', 'Inspect evidence for this unit')}</summary><h4>{label('本段采用的来源', 'Sources used for this unit')}</h4>{sourceLinks(u.id)}<h4>{label('检索到的资料片段', 'Retrieved passages')}</h4>{w.evidence.find(e => e.unit === u.id)?.retrieved.map(r => <blockquote key={r.id}><a href={r.url}>{r.title}</a><p>{r.text}</p></blockquote>)}</details></article>)}
    </section>
  </>

  const shots = <>
    <p className="muted">{label('按成片段落查看选用镜头。点击画面放大；资料图单独标明来源和许可。此处记录已经采用的剪辑选择。', 'Inspect selected footage by narration unit. Click to enlarge; external images retain source and license. These are the choices used in the finished edit.')}</p>
    {w.segments.units.map(u => <section key={u.id} className="card unit-row"><span className="badge badge-accent">{u.id}</span><h3>{u.intent}</h3><p>{u.text.zh}</p>
      <div className="unit-strip">{w.timeline.find(t => t.id === u.id)?.clips.map((c, i) => <article className="cand-thumb example-candidate" key={i}>
        <button className="shot-thumb example-frame-button chosen" onClick={() => setFrame({ file: clipFrame(c), title: clipTitle(c) })}><img src={`${base}/${clipFrame(c)}`} alt={clipTitle(c)} loading="lazy" /><span className="shot-id">{clipTitle(c)}</span></button>
        <p><span className="badge badge-ok">{label('成片选用', 'Used in film')}</span></p>
        {c.attribution && <div className="small"><a href={c.attribution.source_url}>{c.attribution.title}</a><p>{c.attribution.artist} · <a href={c.attribution.license_url}>{c.attribution.license}</a></p></div>}
      </article>)}</div>
    </section>)}
  </>

  const cut = <>
    <p className="muted">{label('按实际输出顺序查看镜头。成片时间来自渲染片段的实际时长，原片时间标明素材出处；配音时间可在下一步查看。', 'Clips appear in output order. Output times use actual rendered clip lengths; source times locate the original footage. Narration timing is shown in the next step.')}</p>
    {w.timeline.map(u => <section className="card unit-row" key={u.id}><div className="row-between"><span className="badge badge-accent">{u.id}</span><span>{clock(u.clips[0].render_start)}–{clock(u.clips.at(-1)!.render_end)}</span></div><h3>{w.segments.units.find(s => s.id === u.id)?.intent}</h3>
      <div className="clip-strip">{u.clips.map((c, i) => <button className="clip-block example-clip" key={i} onClick={() => setFrame({ file: clipFrame(c), title: clipTitle(c) })}><img src={`${base}/${clipFrame(c)}`} alt={clipTitle(c)} loading="lazy" /><span className="clip-info"><strong>{i+1}. {clipTitle(c)}</strong><span>{label('成片', 'Output')} {clock(c.render_start)}–{clock(c.render_end)}</span><span>{c.render_seconds.toFixed(2)}s</span></span></button>)}</div>
    </section>)}
    <p className="small muted">{label('正文画面之后附有概念图、原片与影评署名。完整视频时长', 'Concept-art, film and review credits follow the body. Full video duration')}: {clock(study.movie.duration)}</p>
  </>

  const voice = <>
    <section className="card section"><h2>{label('配音', 'Narration')}</h2><p>{w.timing.voice} · {label('中文合成配音', 'Chinese synthetic narration')}</p><audio controls preload="metadata" src={w.narration_url} aria-label={label('成片中文配音', 'Finished Chinese narration')} />
      <h3>{label('段落配音时间', 'Narration timing')}</h3><table className="timing-table"><thead><tr><th>{label('段落', 'Unit')}</th><th>{label('开始', 'Start')}</th><th>{label('结束', 'End')}</th></tr></thead><tbody>{w.timing.units.map(u => <tr key={u.id}><td>{u.id}</td><td>{u.start.toFixed(2)}s</td><td>{u.end.toFixed(2)}s</td></tr>)}</tbody></table>
    </section>
    <section className="card section"><h2>{label('成片字幕', 'Film subtitles')}</h2><p><a href={`${base}/subtitles.zh.srt`} download>{label('下载中文字幕 SRT', 'Download Chinese SRT')}</a></p><details><summary>{label('展开完整字幕与时间码', 'Read subtitles and timestamps')}</summary><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{w.subtitles}</pre></details></section>
  </>

  const output = <section className="card section"><h2>{study.movie.title}</h2><p className="muted">{study.movie.author} · {clock(study.movie.duration)} · {label('中文解说与字幕', 'Chinese narration and subtitles')}</p>
    <video ref={player} controls playsInline preload="metadata" poster={`${base}/frame-669.jpg`} src={study.movie.url} aria-label={label('Sintel 深度解析成片', 'Sintel finished analysis video')} />
    <p><a href={study.movie.url} className="btn">{label('下载完整解析视频', 'Download full commentary')}</a></p>
    <div className="actions" style={{ flexWrap: 'wrap' }}>{study.movie.chapters.map(ch => <button className="btn btn-small" key={ch.start} onClick={() => { if (player.current) { player.current.currentTime = ch.start; void player.current.play().catch(() => {}); player.current.scrollIntoView({ behavior: 'smooth', block: 'center' }) } }}>{clock(ch.start)} · {ch.title}</button>)}</div>
    <details><summary>{label('展开成片解说词', 'Read the finished narration')}</summary><p style={{ whiteSpace: 'pre-wrap' }}>{study.movie.script}</p></details>
    <p className="small muted">{study.attribution} · <a href={study.license_url}>CC BY 3.0</a> · {study.changes}</p>
  </section>

  return <>
    <ExampleWorkflow title={study.title} steps={steps} intro={label('含完整剧透。按步骤查看这支深度解析视频的实际制作记录。公开示例只读；实时 RAG 与重新剪辑在本地编辑器使用。', 'Contains full spoilers. Explore the actual production records step by step. This public example is read-only; live RAG and editing use the local editor.')}>
      <Routes><Route index element={setup} /><Route path="evidence" element={evidence} /><Route path="script" element={script} /><Route path="shots" element={shots} /><Route path="cut" element={cut} /><Route path="voice" element={voice} /><Route path="export" element={output} /><Route path="*" element={<Navigate to={root} replace />} /></Routes>
    </ExampleWorkflow>
    {frame && <Modal onClose={() => setFrame(null)}><h2>{frame.title}</h2><img className="example-frame-large" src={`${base}/${frame.file}`} alt={frame.title} /></Modal>}
  </>
}
