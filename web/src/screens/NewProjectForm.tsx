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
  const [films, setFilms] = useState<api.FilmEntry[]>([])
  const [styles, setStyles] = useState<Record<Style, api.StyleInfo> | null>(null)
  const [loadingCatalog, setLoadingCatalog] = useState(true)

  const [slug, setSlug] = useState('')
  const [slugTouched, setSlugTouched] = useState(false)
  const [film, setFilm] = useState('')
  const [title, setTitle] = useState('')
  const [style, setStyle] = useState<Style>('recap')
  const [scriptLangs, setScriptLangs] = useState<Lang[]>(['zh'])
  const [subtitleLangs, setSubtitleLangs] = useState<Lang[]>(['zh'])
  const [voiceLangs, setVoiceLangs] = useState<Lang[]>(['zh'])
  const [targetMinutes, setTargetMinutes] = useState(5)
  const [brief, setBrief] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    Promise.all([api.listFilms(), api.listStyles()])
      .then(([f, s]) => {
        setFilms(f)
        setStyles(s)
        if (f.length > 0) setFilm(f[0].path)
      })
      .catch(showError)
      .finally(() => setLoadingCatalog(false))
  }, [showError])

  useEffect(() => {
    if (!slugTouched) setSlug(slugify(title))
  }, [title, slugTouched])

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!slug) return
    setCreating(true)
    try {
      const res = await api.createProject({
        slug,
        film,
        title: title || undefined,
        style,
        script_langs: scriptLangs.length ? scriptLangs : ['zh'],
        subtitle_langs: subtitleLangs,
        voice_langs: voiceLangs,
        target_minutes: targetMinutes,
        brief,
      })
      onCreated(res.slug)
    } catch (e) {
      showError(e)
      setCreating(false)
    }
  }

  return (
    <Modal onClose={onClose}>
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
            <label>{t('newp.film')}</label>
            <select value={film} onChange={(e) => setFilm(e.target.value)} required>
              {films.length === 0 && <option value="">{t('newp.film_pick')}</option>}
              {films.map((f) => (
                <option key={f.path} value={f.path}>
                  {f.name} ({(f.size / 1e6).toFixed(0)} MB)
                </option>
              ))}
            </select>
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
            <button type="button" className="btn" onClick={onClose}>
              {t('common.cancel')}
            </button>
            <button type="submit" className="btn btn-primary" disabled={creating || !film}>
              {creating ? t('newp.creating') : t('newp.create')}
            </button>
          </div>
        </form>
      )}
    </Modal>
  )
}
