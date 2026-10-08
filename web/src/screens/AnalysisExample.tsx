import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import type { ImageCandidate, KnowledgeAnswer, KnowledgeChunk, KnowledgeSource } from '../api'
import { useI18n } from '../i18n'

interface Study {
  title: string
  movie?: { title: string; author: string; duration: number; url: string; chapters: { title: string; start: number; end: number }[]; script: string }
  external_images?: (ImageCandidate & { file: string; changes: string })[]
  saved_run?: KnowledgeAnswer
  sources: KnowledgeSource[]
  chunks: KnowledgeChunk[]
  frames: { time: number; file: string; caption: string }[]
  lenses: { title: string; source_ids: string[]; frames: number[]; draft: string; gap: string }[]
  source_url: string
  license_url: string
  attribution: string
  changes: string
}
const base = `${import.meta.env.BASE_URL}examples/sintel-analysis`
export function AnalysisExample() {
  const { lang } = useI18n()
  const label = (zh: string, en: string) => lang === 'zh' ? zh : en
  const [study, setStudy] = useState<Study | null>(null)
  const [error, setError] = useState('')
  const [query, setQuery] = useState('')
  const [chosen, setChosen] = useState<number[]>([])
  const [notes, setNotes] = useState('')
  const player = useRef<HTMLVideoElement>(null)
  const [insertImage, setInsertImage] = useState(false)
  useEffect(() => {
    const controller = new AbortController()
    fetch(`${base}/study.json`, { signal: controller.signal }).then(r => {
      if (!r.ok) throw new Error(`Could not load study: ${r.status}`)
      return r.json()
    }).then(setStudy).catch(e => { if (!controller.signal.aborted) setError(String(e)) })
    return () => controller.abort()
  }, [])
  if (error) return <p role="alert">{error}</p>
  if (!study) return <p>{label('加载解析样例…', 'Loading analysis study…')}</p>
  const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean)
  const hits = study.chunks.filter(c => !terms.length || terms.some(t => `${c.text} ${c.title}`.toLowerCase().includes(t)))
  function download() {
    const selected = study!.lenses.filter((_, i) => chosen.includes(i))
    const ids = new Set(selected.flatMap(l => l.source_ids))
    const text = [study!.title, '预先编写的解析样例；选择和修改由当前用户完成，未调用实时模型。',
      ...selected.map(l => `## ${l.title}\n${l.draft}\n\n待核实：${l.gap}`),
      `## 我的修改\n${notes}`, '## 来源',
      ...study!.sources.filter(s => ids.has(s.id)).map(s => `${s.title} · ${s.author}\n${s.url}\n${s.rights}`),
      ...(insertImage ? ['## 外部图片插入计划（当前页面预览）', ...(study!.external_images || []).map(i => `${i.title}\n${i.artist}\n${i.source_url}\n${i.license} · ${i.license_url}\n${i.changes}`)] : []),
      '## 电影署名', study!.attribution, study!.license_url, study!.changes].join('\n\n')
    const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown;charset=utf-8' }))
    const link = document.createElement('a'); link.href = url; link.download = 'sintel-analysis-notes.md'; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
  return <div className="analysis-study">
    <Link to="/">← {label('全部项目', 'All projects')}</Link>
    <header className="card section"><span className="badge badge-accent">{label('深度解析 · 完整视频', 'Deep analysis · finished video')}</span><h1>{study.title}</h1>
      <p>{label('从一个论点出发，核对影评与画面，再决定要怎样说。', 'Start with a claim, inspect the review and the footage, then choose what to say.')}</p>
      <p className="muted">{label('本页含完整剧透。先观看中文解析成片，再查看影评依据、原片画面和制作资料。下方笔记可交互修改；实时 RAG 和重新渲染在本地编辑器使用。', 'Contains full spoilers. Watch the finished Chinese commentary, then inspect its sources, film frames and production material. Notes below are interactive; live RAG and re-rendering use the local editor.')}</p>
      <div className="actions"><a className="btn" href={study.source_url}>{label('下载可剪辑原片（官方 ZIP）', 'Download source film (official ZIP)')}</a><a className="btn" href="https://durian.blender.org/sharing">{label('核查官方许可', 'Official license')}</a></div>
      <p className="small muted">{study.attribution} · <a href={study.license_url}>CC BY 3.0</a> · {study.changes}</p>
    </header>
    {study.movie && <section className="card section">
      <h2>{study.movie.title}</h2>
      <p className="muted">{study.movie.author} · {Math.floor(study.movie.duration / 60)}:{String(Math.floor(study.movie.duration % 60)).padStart(2, '0')} · {label('中文解说 / 字幕 / 原片剪辑 / 资料图', 'Chinese narration / subtitles / film excerpts / concept art')}</p>
      <video ref={player} controls playsInline preload="metadata" poster={`${base}/frame-669.jpg`} src={study.movie.url} style={{ width: '100%', borderRadius: 10 }} aria-label={label('Sintel 深度解析成片', 'Sintel finished analysis video')} />
      <p><a href={study.movie.url} className="btn" target="_blank" rel="noreferrer">{label('下载完整解析视频', 'Download full commentary')}</a></p>
      <div className="actions" style={{ flexWrap: 'wrap' }}>{study.movie.chapters.map(ch => <button className="btn btn-small" key={ch.start} onClick={() => { if (player.current) { player.current.currentTime = ch.start; void player.current.play().catch(() => {}); player.current.scrollIntoView({ behavior: 'smooth', block: 'center' }) } }}>{Math.floor(ch.start / 60)}:{String(Math.floor(ch.start % 60)).padStart(2, '0')} · {ch.title}</button>)}</div>
      <details><summary>{label('展开成片解说词', 'Read the finished narration')}</summary><p style={{ whiteSpace: 'pre-wrap' }}>{study.movie.script}</p></details>
    </section>}
    <section className="card section"><h2>{label('1. 核对参考资料', '1. Inspect sources')}</h2>
      <label>{label('筛选摘记（关键词，不调用模型）', 'Filter notes (keywords, no model)')}<input value={query} onChange={e => setQuery(e.target.value)} placeholder="悲剧 / 表情 / 许可 / dragon" /></label>
      <div className="actions">{['悲剧', '表情', '许可', '时间'].map(q => <button className="btn" key={q} onClick={() => setQuery(q)}>{q}</button>)}<button className="btn" onClick={() => setQuery('')}>{label('全部', 'All')}</button></div>
      {!hits.length && <p role="status">{label('没有匹配的资料；不会凭空补出答案。', 'No matching source; no answer is invented.')}</p>}
      {hits.map(c => <article key={c.id} className="card section"><span className="badge">{c.kind === 'review' ? label('影评摘记', 'Review notes') : c.kind === 'production' ? label('官方资料摘记', 'Official source notes') : label('片内观察', 'Film observations')}</span><h3><a href={c.url} target="_blank" rel="noreferrer">{c.title} ↗</a></h3><p style={{ whiteSpace: 'pre-wrap' }}>{c.text}</p><p className="small muted">{c.author} · {c.id}</p><p className="small muted">{c.rights}</p></article>)}
      <details><summary>{label('把这些资料用于本地 RAG', 'Use these sources in local RAG')}</summary><p>{label('下载 JSON 后，以 mococo knowledge add 项目目录 文件路径 导入；也可在“资料与论据”中粘贴摘记和来源。', 'Import JSON with mococo knowledge add PROJECT FILE, or paste its text and metadata in Sources and evidence.')}</p>{['review', 'license', 'observations'].map(name => <p key={name}><a href={`${base}/${name}.json`} download>{name}.json ↓</a></p>)}</details>
    </section>
    {study.saved_run && <section className="card section">
      <h2>{label('一次真实 RAG 运行记录', 'A recorded live RAG run')}</h2>
      <p className="muted">{label('下面是开发验证时通过真实模型生成的记录，尚未作为你的写作依据确认。本页只展示已保存结果，不会为新问题调用模型。', 'A real model response recorded during development, not yet approved as your evidence. This page displays saved results; it does not call a model for new questions.')}</p>
      <h3>{study.saved_run.query}</h3>
      {study.saved_run.claims.map((c, i) => <article key={i}><span className="badge">{c.kind}</span><p>{c.text}</p><details><summary>{label('展开检索依据', 'Inspect retrieved evidence')}</summary>{c.citations.map(id => { const chunk = study.saved_run!.retrieved.find(h => h.id === id); return chunk && <blockquote key={id}><a href={chunk.url}>{chunk.title}</a><p>{chunk.text}</p><small>{chunk.id}</small></blockquote> })}</details></article>)}
      {study.saved_run.gaps.map((gap, i) => <p key={i} className="muted">{gap}</p>)}
    </section>}
    <section><h2>{label('2. 比较画面，审阅解释', '2. Compare frames and review interpretations')}</h2>
      <p className="muted">{label('引用来源不意味着观点已经被证明。时间点对应官方 720p MKV；请回看片段核对。', 'A citation does not prove an interpretation. Timestamps refer to the official 720p MKV; inspect surrounding footage.')}</p>
      {study.lenses.map((l, i) => <article className="card section" key={l.title}><div className="row-between"><h3>{l.title}</h3><label><input type="checkbox" checked={chosen.includes(i)} onChange={e => setChosen(e.target.checked ? [...chosen, i] : chosen.filter(n => n !== i))} /> {label('纳入我的草稿', 'Include in my draft')}</label></div>
        <p>{l.draft}</p><div className="grid-cards">{study.frames.filter(f => l.frames.includes(f.time)).map(f => <figure key={f.time} style={{ margin: 0 }}><img style={{ width: '100%', borderRadius: 8 }} src={`${base}/${f.file}`} alt={f.caption} /><figcaption className="small muted">{Math.floor(f.time / 60)}:{String(f.time % 60).padStart(2, '0')} · {f.caption}</figcaption></figure>)}</div>
        <p className="small">{label('参考', 'Sources')}: {l.source_ids.map(id => { const s = study.sources.find(s => s.id === id)!; return <a key={id} href={s.url} style={{ marginRight: 12 }}>{s.title} ↗</a> })}</p><p className="muted">{label('证据边界', 'Evidence limit')}: {l.gap}</p>
      </article>)}
    </section>
    {!!study.external_images?.length && <section className="card section">
      <h2>{label('3. 外部图片补充制作背景', '3. Context from external images')}</h2>
      <p>{label('以下概念图通过真实 Commons 检索、许可复核与下载流程取得。它可以补充人物设计背景，不能证明剧情事实或导演意图。', 'This concept art was retrieved, checked and downloaded through the live Commons workflow. It adds production context, not proof of plot details or director intent.')}</p>
      {study.external_images.map(i => <figure key={i.id} style={{ margin: 0 }}><img src={`${base}/${i.file}`} alt={i.caption} style={{ maxHeight: 320, maxWidth: '100%', objectFit: 'contain' }} /><figcaption><a href={i.source_url}>{i.title}</a><p>{i.artist} · <a href={i.license_url}>{i.license}</a></p><p className="small muted">{i.changes}</p></figcaption></figure>)}
      <label><input type="checkbox" checked={insertImage} onChange={e => setInsertImage(e.target.checked)} /> {label('在我的草稿中加入这张资料图', 'Include this image in my draft')}</label>
      {insertImage && <p role="status">{label('插入计划：资料图 → 电影画面对照 → 图片署名。导出笔记将保留图片来源和许可。', 'Insert plan: contextual image → film comparison → image credits. Exported notes include its source and license.')}</p>}
      <p className="small muted">{label('本页演示插入计划，不在浏览器渲染视频。本地编辑器的“镜头 → 检索与插入外部图片”会将确认的图片放入时间线，视频导出包含署名片尾。', 'This page previews an insert plan, not browser video rendering. In the local editor, Shots → Find and insert contextual images adds approved images to the timeline and credits to the rendered video.')}</p>
    </section>}
    <section className="card section"><h2>{label('4. 保留你的判断', '3. Keep your own interpretation')}</h2><label>{label('我的修改和需要补查的地方', 'My edits and remaining questions')}<textarea rows={5} value={notes} onChange={e => setNotes(e.target.value)} /></label><p className="small muted">{label('此页选择与修改仅在当前页面保留；离开前请导出。', 'Selections and edits stay on this page only. Export before leaving.')}</p><button className="btn btn-primary" disabled={!chosen.length} onClick={download}>{label('导出选中论点、修改与来源', 'Export selected claims, edits and sources')}</button></section>
  </div>
}
