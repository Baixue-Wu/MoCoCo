import { useEffect, useMemo, useState } from 'react'
import * as api from '../../api'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'
import { useProject } from '../../state/ProjectContext'
import { StageBar } from '../../components/StageBar'
import { Spinner } from '../../components/Spinner'

function basename(p: string): string {
  return p.split('/').pop() ?? p
}

function UnitRow({
  unit,
  cand,
  shots,
  uiLang,
  primaryLang,
  onToggle,
}: {
  unit: api.Unit
  cand: api.UnitCandidates
  shots: Record<string, api.Shot>
  uiLang: string
  primaryLang: string
  onToggle: (shotId: string, nowChosen: boolean) => void
}) {
  const { t } = useI18n()
  const { detail } = useProject()
  const text = unit.text[uiLang] ?? unit.text[primaryLang]
  return (
    <div className="card unit-row">
      <div className="row-between">
        <span className="badge badge-accent">{unit.id}</span>
        <span className="badge">{unit.mood}</span>
      </div>
      <p style={{ marginTop: 8 }}>{text}</p>
      <div className="unit-strip">
        {cand.shots.map((c) => {
          const sh = shots[c.shot_id]
          const chosen = cand.chosen.includes(c.shot_id)
          return (
            <div key={c.shot_id} className="cand-thumb">
              <div
                className={`shot-thumb ${chosen ? 'chosen' : ''}`}
                title={c.why}
                onClick={() => onToggle(c.shot_id, !chosen)}
              >
                <img src={api.mediaFrame(detail!.slug, c.shot_id)} loading="lazy" alt={c.shot_id} />
                <span className="shot-id">{c.shot_id}</span>
                {chosen && <span className="badge badge-accent" style={{ position: 'absolute', top: 4, right: 4 }}>{t('shots.chosen')}</span>}
              </div>
              <div className="cand-meta">
                {t('shots.score', { v: c.score.toFixed(2) })}
                {sh && (
                  <>
                    {' · '}
                    {sh.start.toFixed(1)}-{sh.end.toFixed(1)}s
                  </>
                )}
              </div>
              <div className="cand-meta" style={{ fontStyle: 'italic' }}>
                {c.why}
              </div>
            </div>
          )
        })}
      </div>
      {cand.external.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <h3>{t('shots.external')}</h3>
          <div className="hstack" style={{ flexWrap: 'wrap' }}>
            {cand.external.map((ex, i) => (
              <a key={i} href={ex.source_url} target="_blank" rel="noreferrer" className="card" style={{ width: 150, padding: 6, textDecoration: 'none' }}>
                <img src={api.mediaExternal(detail!.slug, basename(ex.file))} style={{ width: '100%', borderRadius: 6, aspectRatio: '4/3', objectFit: 'cover' }} alt="" />
                <div className="small muted" style={{ marginTop: 4 }}>
                  {ex.caption}
                </div>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function ShotsStep() {
  const { t, lang: uiLang } = useI18n()
  const { detail, refresh } = useProject()
  const { showError, show } = useToast()
  const [segments, setSegments] = useState<api.Segments | null>(null)
  const [candidates, setCandidates] = useState<api.Candidates | null>(null)
  const [shots, setShots] = useState<Record<string, api.Shot>>({})
  const [saving, setSaving] = useState(false)
  const slug = detail?.slug
  const retrieveDone = detail?.status.retrieve

  useEffect(() => {
    if (!slug || !detail?.status.segments) return
    api.getSegments(slug).then(setSegments).catch(showError)
    api
      .getShots(slug)
      .then((list) => setShots(Object.fromEntries(list.map((s) => [s.id, s]))))
      .catch(showError)
  }, [slug, detail?.status.segments, showError])

  useEffect(() => {
    if (!slug || !retrieveDone) {
      setCandidates(null)
      return
    }
    api.getCandidates(slug).then(setCandidates).catch(showError)
  }, [slug, retrieveDone, showError])

  const candByUnit = useMemo(() => {
    const m = new Map<string, api.UnitCandidates>()
    candidates?.units.forEach((u) => m.set(u.unit_id, u))
    return m
  }, [candidates])

  if (!detail) return null

  const toggle = (unitId: string, shotId: string, nowChosen: boolean) => {
    if (!candidates) return
    const next: api.Candidates = {
      units: candidates.units.map((u) =>
        u.unit_id === unitId
          ? { ...u, chosen: nowChosen ? [...u.chosen, shotId] : u.chosen.filter((s) => s !== shotId) }
          : u,
      ),
    }
    setCandidates(next)
    void api.postEvent(slug!, { kind: nowChosen ? 'shot_chosen' : 'shot_unchosen', unit: unitId, shot: shotId })
  }

  const saveChoices = async () => {
    if (!candidates || !slug) return
    setSaving(true)
    try {
      await api.putCandidates(slug, candidates)
      show(t('shots.saved'))
    } catch (e) {
      showError(e)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <StageBar stage="retrieve" done={!!retrieveDone} onDone={refresh} />
      {!detail.status.segments && <p className="muted">{t('shots.no_units')}</p>}
      {detail.status.segments && !retrieveDone && <p className="muted">{t('shots.no_candidates')}</p>}
      {retrieveDone && (!segments || !candidates) && (
        <div className="center-msg">
          <Spinner />
        </div>
      )}
      {retrieveDone && segments && candidates && (
        <>
          <p className="hint">{t('shots.hint')}</p>
          {segments.units.map((u) => {
            const cand = candByUnit.get(u.id)
            if (!cand) return null
            return (
              <UnitRow
                key={u.id}
                unit={u}
                cand={cand}
                shots={shots}
                uiLang={uiLang}
                primaryLang={segments.primary_lang}
                onToggle={(shotId, nowChosen) => toggle(u.id, shotId, nowChosen)}
              />
            )
          })}
          <button className="btn btn-primary" onClick={saveChoices} disabled={saving}>
            {t('shots.save_choices')}
          </button>
        </>
      )}
    </div>
  )
}
