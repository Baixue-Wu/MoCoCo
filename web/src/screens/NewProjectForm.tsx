import { useEffect, useState } from 'react'
import * as api from '../api'
import { useI18n } from '../i18n'
import { useToast } from '../components/Toast'
import { Modal } from '../components/Modal'
import { Spinner } from '../components/Spinner'
import { LangChecks } from '../components/LangChecks'
import type { Lang, Style } from '../api'

function slugify(s: string): string {
  return s
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64)
}

export function NewProjectForm({ onClose, onCreated }: { onClose: () => void; onCreated: (slug: string) => void }) {
  const { t, lang: uiLang } = useI18n()
  const { showError } = useToast()
  const [styles, setStyles] = useState<Record<Style, api.StyleInfo> | null>(null)
  const [loadingCatalog, setLoadingCatalog] = useState(true)

  const [slug, setSlug] = useState('')
  const [fallbackSlug] = useState(() => `project-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`)
  const [slugTouched, setSlugTouched] = useState(false)
  const [localFilm, setLocalFilm] = useState<File | null>(null)
  const [uploadPercent, setUploadPercent] = useState<number | null>(null)
  const [title, setTitle] = useState('')
  const [style, setStyle] = useState<Style>('recap')
  const [scriptLangs, setScriptLangs] = useState<Lang[]>(['zh'])
  const [subtitleLangs, setSubtitleLangs] = useState<Lang[]>(['zh'])
  const [voiceLangs, setVoiceLangs] = useState<Lang[]>(['zh'])
  const [targetMinutes, setTargetMinutes] = useState(5)
  const [brief, setBrief] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    api.listStyles()
      .then(setStyles)
      .catch(showError)
      .finally(() => setLoadingCatalog(false))
  }, [showError])

  useEffect(() => {
    if (!slugTouched) setSlug(slugify(title) || fallbackSlug)
  }, [title, slugTouched, fallbackSlug])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!slug || !localFilm) return
    setCreating(true)
    try {
      const res = await api.createProjectFromFile({
        slug,
        title: title || undefined,
        style,
        script_langs: scriptLangs.length ? scriptLangs : ['zh'],
        subtitle_langs: subtitleLangs,
        voice_langs: voiceLangs,
        target_minutes: targetMinutes,
        brief,
      }, localFilm, setUploadPercent)
      onCreated(res.slug)
    } catch (e) {
      showError(e)
      setCreating(false)
      setUploadPercent(null)
    }
  }

  return (
    <Modal onClose={() => { if (!creating) onClose() }}>
      <h2>{t('newp.title')}</h2>
      {loadingCatalog ? (
        <div className="center-msg">
          <Spinner />
        </div>
      ) : (
        <form onSubmit={submit}>
          <div className="field">
            <label>{t('newp.title_label')}</label>
            <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} required />
          </div>

          <div className="field">
            <label>{t('newp.slug')}</label>
            <input
              type="text"
              value={slug}
              onChange={(e) => {
                setSlugTouched(true)
                setSlug(slugify(e.target.value))
              }}
              required
            />
            <span className="hint">{t('newp.slug_hint')}</span>
          </div>

          <div className="field">
            <label>{t('newp.film_from_computer')}</label>
            <input
              type="file"
              accept=".mp4,.mkv,.mov,.webm,.avi,video/*"
              onChange={(e) => {
                const chosen = e.target.files?.[0] ?? null
                setLocalFilm(chosen)
                if (chosen && !title) setTitle(chosen.name.replace(/\.[^.]+$/, ''))
              }}
            />
            {localFilm && <span className="hint">{t('newp.film_selected', { name: localFilm.name, size: (localFilm.size / 1e6).toFixed(0) })}</span>}
            <span className="hint">{t('newp.film_upload_hint')}</span>
            {uploadPercent !== null && <span className="hint">{t('newp.uploading', { percent: uploadPercent })}</span>}
          </div>

          <div className="field">
            <label>{t('newp.style')}</label>
            <select value={style} onChange={(e) => setStyle(e.target.value as Style)}>
              {styles &&
                Object.entries(styles).map(([key, info]) => (
                  <option key={key} value={key}>
                    {info.label[uiLang]}
                  </option>
                ))}
            </select>
            {styles && <span className="hint">{styles[style].guidance}</span>}
          </div>

          <div className="field">
            <label>{t('newp.script_langs')}</label>
            <LangChecks value={scriptLangs} onChange={setScriptLangs} />
            <span className="hint">{t('newp.langs_hint')}</span>
          </div>

          <div className="field">
            <label>{t('newp.subtitle_langs')}</label>
            <LangChecks value={subtitleLangs} onChange={setSubtitleLangs} />
          </div>

          <div className="field">
            <label>{t('newp.voice_langs')}</label>
            <LangChecks value={voiceLangs} onChange={setVoiceLangs} />
          </div>

          <div className="field">
            <label>{t('newp.target_minutes')}</label>
            <input
              type="number"
              min={1}
              step={0.5}
              value={targetMinutes}
              onChange={(e) => setTargetMinutes(Number(e.target.value))}
            />
          </div>

          <div className="field">
            <label>
              {t('newp.brief')} <span className="hint">({t('common.optional')})</span>
            </label>
            <textarea rows={4} value={brief} onChange={(e) => setBrief(e.target.value)} placeholder={t('newp.brief_placeholder')} />
          </div>

          <div className="hstack" style={{ justifyContent: 'flex-end' }}>
            <button type="button" className="btn" onClick={onClose} disabled={creating}>
              {t('common.cancel')}
            </button>
            <button type="submit" className="btn btn-primary" disabled={creating || !localFilm}>
              {creating ? t('newp.creating') : t('newp.create')}
            </button>
          </div>
        </form>
      )}
    </Modal>
  )
}
