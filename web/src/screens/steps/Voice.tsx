import { useEffect, useRef, useState } from 'react'
import * as api from '../../api'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'
import { useProject } from '../../state/ProjectContext'
import { StageBar } from '../../components/StageBar'
import { Spinner } from '../../components/Spinner'
import { stepDone } from '../../state/steps'

function TimingTable({ slug, lang }: { slug: string; lang: string }) {
  const { t } = useI18n()
  const { showError } = useToast()
  const [timing, setTiming] = useState<api.Timing | null>(null)

  useEffect(() => {
    api.getTiming(slug, lang as api.Lang).then(setTiming).catch(showError)
  }, [slug, lang, showError])

  if (!timing) {
    return (
      <div className="center-msg">
        <Spinner />
      </div>
    )
  }

  return (
    <table className="timing-table">
      <thead>
        <tr>
          <th>{t('voice.timing_unit')}</th>
          <th>{t('voice.timing_start')}</th>
          <th>{t('voice.timing_end')}</th>
        </tr>
      </thead>
      <tbody>
        {timing.units.map((u) => (
          <tr key={u.id}>
            <td>{u.id}</td>
            <td>{u.start.toFixed(2)}s</td>
            <td>{u.end.toFixed(2)}s</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function VoiceLang({ lang }: { lang: string }) {
  const { t } = useI18n()
  const { detail, refresh } = useProject()
  const { showError } = useToast()
  const fileRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const slug = detail!.slug
  const hasNarration = detail!.status.voice[lang]
  const hasUpload = detail!.status.uploads[lang]
  const voiceName = detail!.settings.voice[lang as 'zh' | 'en']

  const onUpload = async (file: File) => {
    setBusy(true)
    try {
      await api.uploadNarration(slug, lang, file)
      await refresh()
    } catch (e) {
      showError(e)
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const removeUpload = async () => {
    setBusy(true)
    try {
      await api.deleteUploadedNarration(slug, lang)
      await refresh()
    } catch (e) {
      showError(e)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card section">
      <div className="row-between">
        <h2 style={{ margin: 0 }}>{t(`newp.lang.${lang}`)}</h2>
        <span className="badge">
          {t('voice.voice_name')}: {voiceName}
        </span>
      </div>

      {hasNarration ? (
        <>
          <audio controls src={api.mediaNarration(slug, lang)} style={{ marginTop: 10 }} />
          <p className="small muted">{hasUpload ? t('voice.uploaded') : t('voice.using_tts')}</p>
        </>
      ) : (
        <p className="muted">{t('voice.no_timing')}</p>
      )}

      <div className="field">
        <label>{t('common.upload')}</label>
        <input
          ref={fileRef}
          type="file"
          accept="audio/*"
          disabled={busy}
          onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])}
        />
        <span className="hint">{t('voice.upload_hint')}</span>
      </div>
      {hasUpload && (
        <button className="btn btn-danger btn-small" onClick={removeUpload} disabled={busy}>
          {t('voice.remove_upload')}
        </button>
      )}

      {hasNarration && (
        <div style={{ marginTop: 16 }}>
          <h3>{t('voice.timing_heading')}</h3>
          <TimingTable slug={slug} lang={lang} />
        </div>
      )}
    </div>
  )
}

export function VoiceStep() {
  const { t } = useI18n()
  const { detail, refresh } = useProject()
  if (!detail) return null
  const langs = detail.settings.voice_langs

  return (
    <div>
      <StageBar stage="voice" done={stepDone('voice', detail.status)} onDone={refresh} />
      {langs.length === 0 && <p className="muted">{t('voice.no_langs')}</p>}
      {langs.map((l) => (
        <VoiceLang key={l} lang={l} />
      ))}
    </div>
  )
}
