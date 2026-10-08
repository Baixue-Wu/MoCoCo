import { useEffect, useState } from 'react'
import * as api from '../api'
import { useI18n } from '../i18n'

export function KnowledgePanel({ slug }: { slug: string }) {
  const { lang } = useI18n()
  const label = (zh: string, en: string) => lang === 'zh' ? zh : en
  const [state, setState] = useState<api.KnowledgeState | null>(null)
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<api.KnowledgeChunk[] | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [source, setSource] = useState<Omit<api.KnowledgeSource, 'id'>>({ title: '', author: '', url: '', rights: '', text: '', kind: 'review' })
  const refresh = () => api.getKnowledge(slug).then(setState)
  useEffect(() => { void api.getKnowledge(slug).then(setState).catch(e => setError(String(e))) }, [slug])
  async function perform(task: () => Promise<unknown>) {
    setBusy(true); setError('')
    try { await task(); await refresh() } catch (e) { setError(String(e)) } finally { setBusy(false) }
  }
  async function suggest() {
    const job = await api.suggestKnowledge(slug, query)
    for (;;) {
      await new Promise(resolve => setTimeout(resolve, 1500))
      const latest = await api.getJob(job.id)
      if (latest.status === 'failed') throw new Error(latest.error || 'Analysis failed')
      if (latest.status === 'done') return
    }
  }
  return <section className="card section" style={{ marginBottom: 24 }}>
    <h2>{label('资料与论据 · RAG', 'Sources and evidence · RAG')}</h2>
    <p className="muted">{label('导入影评或制作背景，检索相关段落，再生成有出处的解读建议。只有你确认的建议会进入下一次 AI 草稿；不会自动覆盖现有文案。', 'Import reviews or production context, retrieve passages, then generate cited suggestions. Only approved suggestions inform the next AI draft; existing scripts are not replaced.')}</p>
    <p className="small muted">{label('当前使用关键词检索（BM25，中英文词项），不是全网搜索或跨语言语义检索。来源不是共识，评论观点不等于导演意图。', 'Uses keyword retrieval (BM25, English tokens and Chinese bigrams), not web search or cross-language semantic retrieval. A source is not consensus; a review is not proof of director intent.')}</p>
    {error && <p className="error-box" role="alert">{error}</p>}
    <details><summary>{label('添加参考资料', 'Add a source')}</summary>
      <form onSubmit={e => { e.preventDefault(); void perform(async () => { await api.addKnowledgeSource(slug, source); setSource({ title: '', author: '', url: '', rights: '', text: '', kind: 'review' }); setHits(null) }) }} className="stack">
        {([['title', '资料标题', 'Title'], ['author', '作者', 'Author'], ['url', '原文链接', 'Source URL'], ['rights', '使用许可／摘记说明', 'Rights or note provenance']] as const).map(([key, zh, en]) => <label key={key}>{label(zh, en)}<input required type={key === 'url' ? 'url' : 'text'} value={source[key]} onChange={e => setSource({ ...source, [key]: e.target.value })} /></label>)}
        <label>{label('资料类型', 'Source type')}<select value={source.kind} onChange={e => setSource({ ...source, kind: e.target.value as api.KnowledgeSource['kind'] })}><option value="review">{label('影评', 'Review')}</option><option value="production">{label('制作背景', 'Production')}</option><option value="creator_note">{label('创作者摘记', 'Creator notes')}</option></select></label>
        <label>{label('资料正文／有权使用的摘记（至少 20 字符）', 'Source text or permitted notes (at least 20 characters)')}<textarea required minLength={20} maxLength={100000} rows={6} value={source.text} onChange={e => setSource({ ...source, text: e.target.value })} /></label>
        <button className="btn" disabled={busy}>{label('保存资料', 'Save source')}</button>
      </form>
    </details>
    <ul>{state?.sources.map(s => <li key={s.id}><a href={s.url} target="_blank" rel="noreferrer">{s.title}</a> · {s.author} <button className="btn" disabled={busy} onClick={() => void perform(async () => { await api.removeKnowledgeSource(slug, s.id); setHits(null) })}>{label('移除', 'Remove')}</button><p className="small muted">{s.rights}</p></li>)}</ul>
    {state?.sources.length === 0 && <p>{label('还没有外部资料。深度解析的风格选择本身不会产生 RAG。', 'No sources yet. Choosing analysis style alone does not supply RAG evidence.')}</p>}
    <label>{label('希望补充哪一项论据？', 'What evidence do you need?')}<textarea rows={2} maxLength={4000} value={query} onChange={e => setQuery(e.target.value)} placeholder={label('例如：梦境如何呈现电影与现实的关系？', 'For example: How does the dream relate cinema to reality?')} /></label>
    <div className="actions"><button className="btn" disabled={busy || !query.trim()} onClick={() => void perform(async () => setHits(await api.searchKnowledge(slug, query)))}>{label('检索资料（不调用模型）', 'Retrieve passages (no model)')}</button><button className="btn btn-primary" disabled={busy || !query.trim() || !state?.sources.length} onClick={() => void perform(suggest)}>{busy ? label('处理中…', 'Working…') : label('检索并生成解读建议', 'Retrieve and generate suggestions')}</button></div>
    <p className="small muted">{label('生成时会将问题与检索到的资料发送给已配置模型。', 'Generation sends your question and retrieved passages to the configured model.')}</p>
    {hits?.length === 0 && <p role="status">{label('未找到相关资料。请补充来源，或使用与资料相同的语言。', 'No relevant passage. Add a source or use the source language.')}</p>}
    {hits?.map(h => <blockquote key={h.id}><a href={h.url}>{h.title}</a><p>{h.text}</p><small>{h.author} · {h.start}–{h.end} · {h.id}</small></blockquote>)}
    {state?.answers.slice().reverse().map(a => <article className="card section" key={a.id}>
      <h3>{a.query}</h3>
      {a.claims.map((c, i) => <div key={i}><span className="badge">{c.kind === 'interpretation' ? label('解读建议', 'Interpretation') : label('来源所述', 'Source reports')}</span><p>{c.text}</p><details><summary>{label('核对依据', 'Inspect evidence')}</summary>{c.citations.map(id => { const h = a.retrieved.find(r => r.id === id); return h && <blockquote key={id}><a href={h.url}>{h.title}</a> · {h.author}<p>{h.text}</p><small>{id} · {h.rights}</small></blockquote> })}</details><p className="small muted">{label('镜头检索线索', 'Visual search cue')}: {c.visual_query}</p></div>)}
      {a.gaps.map((g, i) => <p key={i} className="muted">{label('待核实', 'Evidence gap')}: {g}</p>)}
      {a.source_revision !== state.source_revision && <p role="status">{label('资料已变化，请重新检索后确认。', 'Sources changed. Retrieve again before approving.')}</p>}
      <button className="btn" disabled={busy || (!a.accepted && (!a.claims.length || a.source_revision !== state.source_revision))} onClick={() => void perform(() => api.reviewKnowledge(slug, a.id, !a.accepted))}>{a.accepted ? label('已确认 · 撤回', 'Approved · revoke') : label('确认作为写作依据', 'Approve as draft evidence')}</button>
    </article>)}
  </section>
}
