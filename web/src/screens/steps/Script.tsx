import { useCallback, useEffect, useState, type ReactNode } from 'react'
import * as api from '../../api'
import type { Lang } from '../../api'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'
import { useProject } from '../../state/ProjectContext'
import { StageBar } from '../../components/StageBar'
import { Spinner } from '../../components/Spinner'
import { Modal } from '../../components/Modal'
import { FactCheckParagraphs } from '../../components/FactCheck'

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

function FactCheckButton({ onRun }: { onRun: () => void }) {
  const { t } = useI18n()
  const { jobsByStage, isBusy } = useProject()
  const job = jobsByStage['script.check']
  const running = job?.status === 'running'
  return (
    <span className="hstack gap-sm">
      <button className="btn" disabled={isBusy} onClick={onRun}>
        {running ? <Spinner /> : null} {t('check.button')}
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
  actions,
  children,
}: {
  lang: Lang
  primary: boolean
  text: string
  onChange: (v: string) => void
  onSave: () => void
  saving: boolean
  editedSinceSegment: boolean
  actions?: ReactNode
  children?: ReactNode
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
        {actions}
      </div>
      {children}
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
  const { detail, refresh, runStage, isBusy } = useProject()
  const { showError } = useToast()
  const [report, setReport] = useState<api.CheckReport | null>(null)
  const [snapshot, setSnapshot] = useState<string | null>(null)
  const [accepted, setAccepted] = useState<Set<number>>(new Set())
  const [seek, setSeek] = useState<number | null>(null)
  const [texts, setTexts] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState<Record<string, boolean>>({})
  const [editedSince, setEditedSince] = useState<Record<string, boolean>>({})
  const slug = detail?.slug
  const scriptStatusKey = detail ? JSON.stringify(detail.status.script) : ''

  const loadTexts = useCallback(async () => {
    if (!detail) return
    const pairs = await Promise.all(
      detail.settings.script_langs.map((l) =>
        api
          .getScript(slug!, l)
          .then((r) => [l, r.text] as const)
          .catch(() => [l, ''] as const),
      ),
    )
    setTexts(Object.fromEntries(pairs))
    return Object.fromEntries(pairs) as Record<string, string>
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, detail?.settings.script_langs.join(',')])

  // the report belongs to the script as saved on the server; remember that text so
  // any later difference in the editor marks the report stale
  const loadReport = useCallback(async () => {
    if (!slug || !detail) return
    try {
      const [r, sc] = await Promise.all([api.getCheck(slug), api.getScript(slug, detail.settings.script_langs[0])])
      setReport(r)
      setSnapshot(sc.text)
      setAccepted(new Set())
    } catch {
      setReport(null)
      setSnapshot(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, detail?.settings.script_langs[0]])

  useEffect(() => {
    void loadTexts()
  }, [loadTexts, scriptStatusKey])

  const checkDone = detail?.status.check
  useEffect(() => {
    if (checkDone) void loadReport()
    else setReport(null)
  }, [checkDone, loadReport])

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

  const runCheck = async (fix: boolean) => {
    if (fix && !window.confirm(t('check.confirm_fix'))) return
    try {
      await runStage('script.check', { fix })
      if (fix) await loadTexts()
      await loadReport()
    } catch {
      /* shown on the button */
    }
  }

  const primaryText = texts[primary]
  const stale = !!report && snapshot !== null && primaryText !== undefined && primaryText !== snapshot

  const accept = (para: api.CheckParagraph) => {
    if (!para.revised) return
    const paras = paragraphs(texts[primary] ?? '')
    if (para.index >= paras.length) return
    paras[para.index] = para.revised
    const next = paras.join('\n\n') + '\n'
    setTexts((cur) => ({ ...cur, [primary]: next }))
    setEditedSince((cur) => ({ ...cur, [primary]: true }))
    setSnapshot(next)
    setAccepted((cur) => new Set(cur).add(para.index))
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
            actions={l === primary ? <FactCheckButton onRun={() => runCheck(false)} /> : undefined}
          >
            {l === primary && report && (
              <FactCheckParagraphs
                report={report}
                stale={stale}
                accepted={accepted}
                onSeek={setSeek}
                onAccept={accept}
                onAcceptAll={() => runCheck(true)}
                busy={isBusy}
              />
            )}
          </ScriptColumn>
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
      {seek !== null && (
        <Modal onClose={() => setSeek(null)}>
          <video key={seek} controls autoPlay src={`${api.mediaFilm(slug!)}#t=${seek}`} />
        </Modal>
      )}
    </div>
  )
}
