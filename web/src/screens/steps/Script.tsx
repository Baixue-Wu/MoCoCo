import { useEffect, useState } from 'react'
import * as api from '../../api'
import type { Lang } from '../../api'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'
import { useProject } from '../../state/ProjectContext'
import { StageBar } from '../../components/StageBar'
import { Spinner } from '../../components/Spinner'

function paragraphs(text: string): string[] {
  return text
    .replace(/\r\n/g, '\n')
    .split('\n\n')
    .map((p) => p.trim())
    .filter(Boolean)
}

// A slim inline run/redo control, for use beside a textarea's save button
// (StageBar is used for the page-level segment stage instead).
function StageBarInline({ stage, done, extra, confirm }: { stage: string; done: boolean; extra?: api.StageRequest; confirm?: string }) {
  const { t } = useI18n()
  const { jobsByStage, isBusy, runStage } = useProject()
  const job = jobsByStage[stage]
  const running = job?.status === 'running'

  const go = async () => {
    if (confirm && done && !window.confirm(confirm)) return
    try {
      await runStage(stage, extra)
    } catch {
      /* surfaced via job.error below */
    }
  }

  return (
    <span className="hstack gap-sm">
      <button className="btn" disabled={isBusy && !running} onClick={go}>
        {running ? (
          <>
            <Spinner /> {t('wizard.running', { stage })}
          </>
        ) : done ? (
          t('wizard.redo_step')
        ) : (
          t('wizard.run_step')
        )}
      </button>
      {job?.status === 'failed' && (
        <span className="small" style={{ color: 'var(--danger)' }}>
          {job.error?.slice(0, 200)}
        </span>
      )}
    </span>
  )
}

function ScriptColumn({
  lang,
  primary,
  text,
  onChange,
  onSave,
  saving,
  editedSinceSegment,
}: {
  lang: Lang
  primary: boolean
  text: string
  onChange: (v: string) => void
  onSave: () => void
  saving: boolean
  editedSinceSegment: boolean
}) {
  const { t } = useI18n()
  const { detail } = useProject()
  const count = paragraphs(text).length

  return (
    <div className="card section">
      <div className="row-between">
        <h3 style={{ margin: 0 }}>
          {t(`newp.lang.${lang}`)} {primary && <span className="badge badge-accent">primary</span>}
        </h3>
        <span className="small muted">{t('script.paragraphs', { n: count })}</span>
      </div>
      <textarea
        rows={16}
        value={text}
        onChange={(e) => onChange(e.target.value)}
        placeholder={t('script.placeholder')}
        style={{ marginTop: 10 }}
      />
      {editedSinceSegment && detail?.status.segments && (
        <p className="hint" style={{ color: 'var(--danger)' }}>
          {t('script.resegment_hint')}
        </p>
      )}
      <div className="hstack" style={{ marginTop: 8 }}>
        <button className="btn" onClick={onSave} disabled={saving}>
          {t('common.save')}
        </button>
        {primary ? (
          <StageBarInline stage="script.draft" done={!!detail?.status.script[lang]} confirm={t('script.confirm_overwrite')} />
        ) : (
          <StageBarInline stage="script.translate" done={!!detail?.status.script[lang]} extra={{ lang }} />
        )}
      </div>
    </div>
  )
}

function UnitsList() {
  const { t } = useI18n()
  const { detail } = useProject()
  const { showError } = useToast()
  const [segments, setSegments] = useState<api.Segments | null>(null)
  const slug = detail!.slug
  const segmentsDone = detail?.status.segments

  useEffect(() => {
    if (segmentsDone) {
      api.getSegments(slug).then(setSegments).catch(showError)
    } else {
      setSegments(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [segmentsDone])

  if (!segmentsDone) {
    return <p className="muted">{t('script.no_units')}</p>
  }
  if (!segments) {
    return (
      <div className="center-msg">
        <Spinner />
      </div>
    )
  }

  return (
    <div className="grid-cards">
      {segments.units.map((u) => (
        <div key={u.id} className="card section">
          <div className="row-between">
            <span className="badge badge-accent">{u.id}</span>
            <span className="badge">{u.intent}</span>
          </div>
          <p style={{ marginTop: 8 }}>{u.text[segments.primary_lang]}</p>
          <div className="small muted">
            {t('setup.mood')}: {u.mood}
          </div>
          <div className="small muted">
            {t('script.visual_query')}: {u.visual_query_en}
          </div>
          {u.keywords.length > 0 && (
            <div className="small muted">
              {t('script.keywords')}: {u.keywords.join(', ')}
            </div>
          )}
          {u.needs_context && <span className="badge">{t('script.needs_context')}</span>}
        </div>
      ))}
    </div>
  )
}

export function ScriptStep() {
  const { t } = useI18n()
  const { detail, refresh } = useProject()
  const { showError } = useToast()
  const [texts, setTexts] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState<Record<string, boolean>>({})
  const [editedSince, setEditedSince] = useState<Record<string, boolean>>({})
  const slug = detail?.slug
  const scriptStatusKey = detail ? JSON.stringify(detail.status.script) : ''

  useEffect(() => {
    if (!detail) return
    Promise.all(
      detail.settings.script_langs.map((l) =>
        api
          .getScript(slug!, l)
          .then((r) => [l, r.text] as const)
          .catch(() => [l, ''] as const),
      ),
    ).then((pairs) => setTexts(Object.fromEntries(pairs)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, scriptStatusKey])

  if (!detail) return null
  const langs = detail.settings.script_langs
  const primary = langs[0]

  const save = async (lang: Lang) => {
    setSaving((s) => ({ ...s, [lang]: true }))
    try {
      await api.putScript(slug!, lang, texts[lang] ?? '')
      await refresh()
    } catch (e) {
      showError(e)
    } finally {
      setSaving((s) => ({ ...s, [lang]: false }))
    }
  }

  const counts = langs.map((l) => paragraphs(texts[l] ?? '').length)
  const mismatch = counts.length > 1 && new Set(counts).size > 1

  return (
    <div>
      <div className={langs.length === 2 ? 'two-col' : 'stack'}>
        {langs.map((l) => (
          <ScriptColumn
            key={l}
            lang={l}
            primary={l === primary}
            text={texts[l] ?? ''}
            onChange={(v) => {
              setTexts((cur) => ({ ...cur, [l]: v }))
              setEditedSince((cur) => ({ ...cur, [l]: true }))
            }}
            onSave={() => save(l)}
            saving={!!saving[l]}
            editedSinceSegment={!!editedSince[l]}
          />
        ))}
      </div>
      {mismatch && (
        <p className="small" style={{ color: 'var(--danger)' }}>
          {t('script.mismatch', { a: counts[0], b: counts[1] })}
        </p>
      )}
      <StageBar stage="script.segment" done={detail.status.segments} onDone={refresh} />
      <h2 style={{ marginTop: 24 }}>{t('script.units_heading')}</h2>
      <UnitsList />
    </div>
  )
}
