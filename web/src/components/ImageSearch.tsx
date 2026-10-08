import { useEffect, useState } from 'react'
import * as api from '../api'
import { useI18n } from '../i18n'

export function ImageSearch({ slug, unit, initialQuery, approved, onChanged }: { slug: string; unit: string; initialQuery: string; approved: api.ExternalRef[]; onChanged: () => Promise<void> }) {
  const { lang } = useI18n()
  const label = (zh: string, en: string) => lang === 'zh' ? zh : en
  const [query, setQuery] = useState(initialQuery)
  const [data, setData] = useState<api.ImageResults>({ results: [] })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { void api.getImageResults(slug, unit).then(setData).catch(e => setError(String(e))) }, [slug, unit])
  async function act(fn: () => Promise<unknown>) {
    setError(''); setBusy(true)
    try { await fn() } catch (e) { setError(String(e)) } finally { setBusy(false) }
  }
  return <details className="card section">
    <summary>{label('检索与插入外部图片', 'Find and insert contextual images')}</summary>
    <p className="small muted">{label('检索 Wikimedia Commons 中带明确 CC BY、CC0 或公有领域许可及作者的位图。结果来自外部资料，不能当作电影原镜头。选择前请核对相关性与许可；确认后下载并插入本段开头，可在剪辑页调整。', 'Search Wikimedia Commons for attributed raster images with CC BY, CC0 or public-domain metadata. These are contextual sources, not film footage. Review relevance and terms before approval; approved images are inserted at the start of this unit and can be edited in Cut.')}</p>
    <label>{label('图片检索词（英文通常更易匹配）', 'Image query (English often matches better)')}<input maxLength={300} value={query} onChange={e => setQuery(e.target.value)} /></label>
    <button className="btn" disabled={busy || !query.trim()} onClick={() => void act(async () => { setData({ results: [] }); setData(await api.searchImages(slug, unit, query)); await onChanged() })}>{busy ? label('处理中…', 'Working…') : label('检索外部图片', 'Search external images')}</button>
    {error && <p role="alert" className="error-box">{error}</p>}
    {data.status === 'no_eligible_images' && <p role="status">{label('没有找到同时满足检索词、格式和许可条件的图片，请改写检索词。', 'No matching image with supported format and license. Try different terms.')}</p>}
    <div className="grid-cards">{data.results.map(image => {
      const used = approved.some(r => r.id === image.id && r.approved)
      return <article className="card section" key={image.id}>
        <img src={`/api/projects/${encodeURIComponent(slug)}/images/${encodeURIComponent(unit)}/${image.id}/preview`} alt={image.caption} style={{ width: '100%', height: 220, objectFit: 'contain' }} loading="lazy" />
        <h4>{image.title}</h4><p className="small">{image.artist} · <a href={image.license_url} target="_blank" rel="noreferrer">{image.license}</a></p>
        <a href={image.source_url} target="_blank" rel="noreferrer">{label('核对原始页面', 'Inspect original page')} ↗</a><p className="small muted">{image.caption}</p>{image.restrictions && <p>{image.restrictions}</p>}
        <button className="btn" disabled={busy} onClick={() => void act(async () => { if (used) await api.revokeImage(slug, unit, image.id); else await api.approveImage(slug, unit, image.id); await onChanged() })}>{used ? label('已插入 · 撤回', 'Inserted · revoke') : label('确认许可并插入本段', 'Approve terms and insert')}</button>
      </article>
    })}</div>
    {approved.filter(r => r.approved && !data.results.some(i => i.id === r.id)).map(r => <p key={r.id}>{r.title} · {r.artist}<button className="btn" disabled={busy} onClick={() => void act(async () => { await api.revokeImage(slug, unit, r.id!); await onChanged() })}>{label('撤回已插入图片', 'Revoke inserted image')}</button></p>)}
  </details>
}
