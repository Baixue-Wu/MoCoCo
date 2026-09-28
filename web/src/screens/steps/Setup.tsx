import { useEffect, useState } from 'react'
import * as api from '../../api'
import type { Lang, Settings, Style } from '../../api'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'
import { useProject } from '../../state/ProjectContext'
import { StageBar } from '../../components/StageBar'
import { LangChecks } from '../../components/LangChecks'
import { Modal } from '../../components/Modal'
import { Spinner } from '../../components/Spinner'
import { RateSelect, VoiceSelect, VoicePreviewButton } from '../../components/VoiceControls'

function fmtDuration(s: number): string {
  const m = Math.floor(s / 60)
  const sec = Math.round(s % 60)
  return `${m}:${sec.toString().padStart(2, '0')}`
}

function SettingsForm() {
  const { t, lang: uiLang } = useI18n()
  const { detail, refresh } = useProject()
  const { showError, show } = useToast()
  const [styles, setStyles] = useState<Record<Style, api.StyleInfo> | null>(null)
  const [form, setForm] = useState<Settings | null>(detail?.settings ?? null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setForm(detail?.settings ?? null)
  }, [detail?.settings])

  useEffect(() => {
    api.listStyles().then(setStyles).catch(showError)
  }, [showError])

  if (!form) return null

  const save = async () => {
    setSaving(true)
    try {
      await api.putSettings(detail!.slug, form)
      await refresh()
      show(t('setup.settings_saved'))
    } catch (e) {
      showError(e)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="card section">
      <h2>{t('setup.settings')}</h2>
      <div className="field">
        <label>{t('setup.title')}</label>
        <input type="text" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
      </div>
      <div className="field">
        <label>{t('setup.style')}</label>
        <select value={form.style} onChange={(e) => setForm({ ...form, style: e.target.value as Style })}>
          {styles &&
            Object.entries(styles).map(([key, info]) => (
              <option key={key} value={key}>
                {info.label[uiLang]}
              </option>
            ))}
        </select>
        {styles && <span className="hint">{styles[form.style].guidance}</span>}
      </div>
      <div className="field">
        <label>{t('setup.script_langs')}</label>
        <LangChecks value={form.script_langs} onChange={(v) => setForm({ ...form, script_langs: v as Lang[] })} />
      </div>
      <div className="field">
        <label>{t('setup.subtitle_langs')}</label>
        <LangChecks value={form.subtitle_langs} onChange={(v) => setForm({ ...form, subtitle_langs: v as Lang[] })} />
      </div>
      <div className="field">
        <label>{t('setup.voice_langs')}</label>
        <LangChecks value={form.voice_langs} onChange={(v) => setForm({ ...form, voice_langs: v as Lang[] })} />
      </div>
      <div className="field">
        <label>{t('setup.target_minutes')}</label>
        <input
          type="number"
          min={1}
          step={0.5}
          value={form.target_minutes}
          onChange={(e) => setForm({ ...form, target_minutes: Number(e.target.value) })}
        />
      </div>
      <div className="field">
        <label>{t('setup.brief')}</label>
        <textarea rows={4} value={form.brief} onChange={(e) => setForm({ ...form, brief: e.target.value })} />
      </div>
      <div className="field">
        <label>{t('setup.voice_names')}</label>
        <div className="stack gap-sm">
          {form.voice_langs.map((l) => (
            <div key={l} className="hstack">
              <span className="badge">{l}</span>
              <VoiceSelect lang={l} value={form.voice[l]} onChange={(name) => setForm({ ...form, voice: { ...form.voice, [l]: name } })} />
              <VoicePreviewButton lang={l} voice={form.voice[l]} rate={form.voice.rate} />
            </div>
          ))}
        </div>
      </div>
      <div className="field">
        <label>{t('setup.voice_rate')}</label>
        <RateSelect value={form.voice.rate} onChange={(rate) => setForm({ ...form, voice: { ...form.voice, rate } })} />
      </div>
      <button className="btn btn-primary" onClick={save} disabled={saving}>
        {t('common.save')}
      </button>
    </div>
  )
}

function FilmInfo() {
  const { t } = useI18n()
  const { detail } = useProject()
  if (!detail?.film) return null
  const f = detail.film
  return (
    <div className="card section">
      <h2>{t('setup.film_info')}</h2>
      <div className="kv-grid">
        <div>
          <div className="k">{t('setup.film_duration')}</div>
          {fmtDuration(f.duration)}
        </div>
        <div>
          <div className="k">{t('setup.film_resolution')}</div>
          {f.width}×{f.height}
        </div>
        <div>
          <div className="k">{t('setup.film_fps')}</div>
          {f.fps.toFixed(2)}
        </div>
        <div>
          <div className="k">{t('setup.film_audio')}</div>
          {f.has_audio ? '✓' : '—'}
        </div>
      </div>
    </div>
  )
}

function ShotGrid() {
  const { t, lang: uiLang } = useI18n()
  const { detail, jobsByStage } = useProject()
  const [shots, setShots] = useState<api.Shot[] | null>(null)
  const [captions, setCaptions] = useState<api.Captions | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const { showError } = useToast()
  const slug = detail!.slug

  const load = () => {
    if (!detail?.status.ingest) return
    Promise.all([api.getShots(slug), api.getCaptions(slug)])
      .then(([s, c]) => {
        setShots(s)
        setCaptions(c)
      })
      .catch(showError)
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail?.status.ingest, jobsByStage['ingest']?.status])

  return (
    <div className="card section">
      <h2>{t('setup.shots_heading')}</h2>
      {!detail?.status.ingest && <p className="muted">{t('setup.no_shots')}</p>}
      {detail?.status.ingest && !shots && (
        <div className="center-msg">
          <Spinner />
        </div>
      )}
      {shots && captions && (
        <>
          <p className="hint">{t('setup.shots_hint')}</p>
          <div className="shot-grid">
            {shots.map((sh) => {
              const c = captions[sh.id]
              const desc = uiLang === 'zh' ? c?.description_zh : c?.description_en
              return (
                <div key={sh.id} className="shot-thumb" onClick={() => setPreview(sh.id)}>
                  <img src={api.mediaFrame(slug, sh.id)} loading="lazy" alt={sh.id} />
                  <span className="shot-id">{sh.id}</span>
                  {c && (
                    <div className="shot-caption">
                      <div>{desc}</div>
                      <div className="muted">
                        {t('setup.mood')}: {c.mood}
                      </div>
                      {c.tags.length > 0 && <div className="muted">{t('setup.tags')}: {c.tags.join(', ')}</div>}
                      {c.dialogue && <div className="muted">{t('setup.dialogue')}: {c.dialogue}</div>}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </>
      )}
      {preview && (
        <Modal onClose={() => setPreview(null)}>
          <video controls autoPlay src={api.mediaPreview(slug, preview)} />
        </Modal>
      )}
    </div>
  )
}

export function SetupStep() {
  const { detail, refresh } = useProject()
  if (!detail) return null
  return (
    <div>
      <StageBar stage="ingest" done={detail.status.ingest} onDone={refresh} confirmRedo={undefined} />
      <SettingsForm />
      <FilmInfo />
      <ShotGrid />
    </div>
  )
}
