import { useState } from 'react'
import type { CheckClaim, CheckParagraph, CheckReport } from '../api'
import { useI18n } from '../i18n'

export function mmss(t: number): string {
  const s = Math.max(0, Math.round(t))
  return `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`
}

export function FactCheckSummary({ report }: { report: CheckReport }) {
  const { t } = useI18n()
  return (
    <div className="check-summary">
      <span className="c-green">{t('check.supported', { n: report.counts.supported })}</span>
      <span className="c-red">{t('check.contradicted', { n: report.counts.contradicted })}</span>
      <span className="c-amber">{t('check.unsupported', { n: report.counts.unsupported })}</span>
    </div>
  )
}

function ClaimBox({ claim, onSeek }: { claim: CheckClaim; onSeek: (sec: number) => void }) {
  const { t } = useI18n()
  const red = claim.verdict === 'contradicted'
  return (
    <div className="check-claim">
      <span className={`badge ${red ? 'badge-red' : 'badge-amber'}`}>
        {red ? t('check.verdict_contradicted') : t('check.verdict_unsupported')}
      </span>
      <p style={{ margin: '6px 0 2px' }}>{claim.claim}</p>
      {claim.note && (
        <p className="small muted" style={{ margin: 0 }}>
          {t('check.note')}: {claim.note}
        </p>
      )}
      {claim.evidence.map((ev, i) => (
        <div key={i} className="evidence">
          {ev.kind === 'brief' ? (
            <span className="badge">{t('check.ev_brief')}</span>
          ) : (
            <>
              <button className="ts-link" title={t('check.open_film')} onClick={() => onSeek(ev.t)}>
                {mmss(ev.t)}
              </button>
              <span className="muted">{t(`check.ev_${ev.kind}`)}</span>
            </>
          )}
          <span>{ev.text}</span>
        </div>
      ))}
    </div>
  )
}

function ParagraphCard({
  para,
  onSeek,
  onAccept,
  accepted,
  canAccept,
}: {
  para: CheckParagraph
  onSeek: (sec: number) => void
  onAccept: () => void
  accepted: boolean
  canAccept: boolean
}) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const flagged = para.claims.filter((c) => c.verdict !== 'supported')
  const contradicted = flagged.some((c) => c.verdict === 'contradicted')
  const revised = contradicted && para.revised && para.revised !== para.text ? para.revised : null
  return (
    <div className={`check-para ${contradicted ? 'red' : 'amber'}`} onClick={() => setOpen((o) => !o)}>
      <div className="small muted">{t('check.paragraph', { n: para.index + 1 })}</div>
      <div>{para.text}</div>
      {open && (
        <div className="check-panel" onClick={(e) => e.stopPropagation()}>
          {flagged.map((c, i) => (
            <ClaimBox key={i} claim={c} onSeek={onSeek} />
          ))}
          {revised && (
            <>
              <div className="revise-box">
                <div>
                  <div className="small muted">{t('check.before')}</div>
                  {para.text}
                </div>
                <div className="after">
                  <div className="small muted">{t('check.after')}</div>
                  {revised}
                </div>
              </div>
              {accepted ? (
                <span className="small muted">{t('check.accepted')}</span>
              ) : (
                <button className="btn btn-small btn-primary" style={{ alignSelf: 'flex-start' }} disabled={!canAccept} onClick={onAccept}>
                  {t('check.accept')}
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}

export function FactCheckParagraphs({
  report,
  stale,
  accepted,
  onSeek,
  onAccept,
  onAcceptAll,
  busy,
}: {
  report: CheckReport
  stale: boolean
  accepted: Set<number>
  onSeek: (sec: number) => void
  onAccept: (para: CheckParagraph) => void
  onAcceptAll: () => void
  busy: boolean
}) {
  const { t } = useI18n()
  const flagged = report.paragraphs.filter((p) => p.claims.some((c) => c.verdict !== 'supported'))
  const hasFixes = !report.applied && flagged.some((p) => p.claims.some((c) => c.verdict === 'contradicted'))
  return (
    <div style={{ marginTop: 12 }}>
      <FactCheckSummary report={report} />
      {stale && (
        <p className="hint" style={{ color: 'var(--danger)', marginTop: 6 }}>
          {t('check.stale')}
        </p>
      )}
      {report.applied && <p className="hint">{t('check.applied')}</p>}
      {flagged.length === 0 && <p className="hint">{t('check.all_clear')}</p>}
      {flagged.map((p) => (
        <ParagraphCard
          key={p.index}
          para={p}
          onSeek={onSeek}
          onAccept={() => onAccept(p)}
          accepted={accepted.has(p.index)}
          canAccept={!stale && !report.applied}
        />
      ))}
      {hasFixes && (
        <button className="btn btn-small" style={{ marginTop: 10 }} disabled={busy} onClick={onAcceptAll}>
          {t('check.accept_all')}
        </button>
      )}
    </div>
  )
}
