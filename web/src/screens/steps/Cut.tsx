import { useEffect, useState } from 'react'
import * as api from '../../api'
import { isImageClip, pickWhy } from '../../api'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'
import { useProject } from '../../state/ProjectContext'
import { StageBar } from '../../components/StageBar'
import { Spinner } from '../../components/Spinner'
import { Modal } from '../../components/Modal'

const PX_PER_SEC = 16

function basename(p: string): string {
  return p.split('/').pop() ?? p
}

function clipRef(c: api.Clip): string {
  return isImageClip(c) ? c.file : c.shot_id
}

function recomputeSeconds(clip: api.ShotClip): api.ShotClip {
  return { ...clip, seconds: Math.max(0, Math.round((clip.out - clip.in) * 1000) / 1000) }
}

function ClipCard({
  clip,
  slug,
  onInOut,
  onSeconds,
  onDelete,
  onMove,
  isFirst,
  isLast,
}: {
  clip: api.Clip
  slug: string
  onInOut: (field: 'in' | 'out', v: number) => void
  onSeconds: (v: number) => void
  onDelete: () => void
  onMove: (dir: -1 | 1) => void
  isFirst: boolean
  isLast: boolean
}) {
  const { t, lang: uiLang } = useI18n()
  const width = Math.max(70, Math.round(clip.seconds * PX_PER_SEC))
  const image = isImageClip(clip)

  return (
    <div className="clip-block" style={{ width }} title={image ? clip.caption : pickWhy(clip, uiLang)}>
      <img
        src={image ? api.mediaExternal(slug, basename(clip.file)) : api.mediaFrame(slug, clip.shot_id)}
        alt={image ? clip.caption : clip.shot_id}
        loading="lazy"
      />
      <div className="clip-info">
        <div className="hstack" style={{ justifyContent: 'space-between' }}>
          <span className="badge" style={{ alignSelf: 'flex-start' }}>
            {image ? basename(clip.file) : clip.shot_id}
          </span>
          {image && <span className="badge badge-accent">{t('cut.reference')}</span>}
        </div>
        <span className="muted">{clip.seconds.toFixed(1)}s</span>
        {image ? (
          <div className="clip-inputs">
            <input
              type="number"
              step={0.1}
              min={0.1}
              value={clip.seconds}
              onChange={(e) => onSeconds(Number(e.target.value))}
              title={t('cut.seconds')}
            />
          </div>
        ) : (
          <div className="clip-inputs">
            <input
              type="number"
              step={0.1}
              value={clip.in}
              onChange={(e) => onInOut('in', Number(e.target.value))}
              title={t('cut.in')}
            />
            <input
              type="number"
              step={0.1}
              value={clip.out}
              onChange={(e) => onInOut('out', Number(e.target.value))}
              title={t('cut.out')}
            />
          </div>
        )}
        <div className="clip-buttons">
          <button className="btn btn-small" disabled={isFirst} onClick={() => onMove(-1)} title={t('cut.up')}>
            ↑
          </button>
          <button className="btn btn-small" disabled={isLast} onClick={() => onMove(1)} title={t('cut.down')}>
            ↓
          </button>
          <button className="btn btn-small btn-danger" onClick={onDelete} title={t('cut.delete_clip')}>
            ×
          </button>
        </div>
      </div>
    </div>
  )
}

function AddFromCandidates({
  slug,
  unitId,
  candidates,
  onAdd,
  onClose,
}: {
  slug: string
  unitId: string
  candidates: api.UnitCandidates | undefined
  onAdd: (clip: api.Clip) => void
  onClose: () => void
}) {
  const { t } = useI18n()
  return (
    <Modal onClose={onClose}>
      <h2>{t('cut.pick_a_shot')}</h2>
      <div className="unit-strip">
        {(candidates?.shots ?? []).map((c) => (
          <div key={c.shot_id} className="cand-thumb">
            <div
              className="shot-thumb"
              onClick={() => {
                onAdd({ shot_id: c.shot_id, in: 0, out: 3, seconds: 3, why: c.why ?? '', why_zh: c.why_zh })
                onClose()
              }}
            >
              <img src={api.mediaFrame(slug, c.shot_id)} alt={c.shot_id} loading="lazy" />
              <span className="shot-id">{c.shot_id}</span>
            </div>
            <div className="cand-meta">{unitId}</div>
          </div>
        ))}
      </div>
      {candidates && candidates.external.length > 0 && (
        <>
          <h2 style={{ marginTop: 16 }}>{t('shots.external')}</h2>
          <div className="unit-strip">
            {candidates.external.map((ex, i) => (
              <div key={i} className="cand-thumb">
                <div
                  className="shot-thumb"
                  title={ex.caption}
                  onClick={() => {
                    onAdd({ kind: 'image', file: ex.file, caption: ex.caption, seconds: 3 })
                    onClose()
                  }}
                >
                  <img src={api.mediaExternal(slug, basename(ex.file))} alt={ex.caption} loading="lazy" />
                  <span className="shot-id">{t('cut.reference')}</span>
                </div>
                <div className="cand-meta">{ex.caption}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </Modal>
  )
}

export function CutStep() {
  const { t } = useI18n()
  const { detail, refresh } = useProject()
  const { showError, show } = useToast()
  const [timeline, setTimeline] = useState<api.Timeline | null>(null)
  const [candidates, setCandidates] = useState<api.Candidates | null>(null)
  const [saving, setSaving] = useState(false)
  const [addingTo, setAddingTo] = useState<string | null>(null)
  const slug = detail?.slug
  const cutDone = detail?.status.cut

  useEffect(() => {
    if (!slug || !cutDone) {
      setTimeline(null)
      return
    }
    api.getTimeline(slug).then(setTimeline).catch(showError)
    if (detail?.status.retrieve) api.getCandidates(slug).then(setCandidates).catch(showError)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug, cutDone])

  if (!detail) return null

  const updateUnitClips = (unitId: string, clips: api.Clip[]) => {
    if (!timeline) return
    setTimeline({ ...timeline, units: timeline.units.map((u) => (u.id === unitId ? { ...u, clips } : u)) })
  }

  const move = (unitId: string, idx: number, dir: -1 | 1) => {
    const unit = timeline!.units.find((u) => u.id === unitId)!
    const clips = [...unit.clips]
    const j = idx + dir
    if (j < 0 || j >= clips.length) return
    ;[clips[idx], clips[j]] = [clips[j], clips[idx]]
    updateUnitClips(unitId, clips)
    void api.postEvent(slug!, { kind: 'clip_reordered', unit: unitId, clip: clipRef(unit.clips[idx]) })
  }

  const del = (unitId: string, idx: number) => {
    const unit = timeline!.units.find((u) => u.id === unitId)!
    const removed = unit.clips[idx]
    updateUnitClips(unitId, unit.clips.filter((_, i) => i !== idx))
    void api.postEvent(slug!, { kind: 'clip_deleted', unit: unitId, clip: clipRef(removed) })
  }

  const inOut = (unitId: string, idx: number, field: 'in' | 'out', v: number) => {
    const unit = timeline!.units.find((u) => u.id === unitId)!
    const clips = unit.clips.map((c, i) => (i === idx && !isImageClip(c) ? recomputeSeconds({ ...c, [field]: v }) : c))
    updateUnitClips(unitId, clips)
    void api.postEvent(slug!, { kind: 'clip_trimmed', unit: unitId, clip: clipRef(clips[idx]), field, value: v })
  }

  const seconds = (unitId: string, idx: number, v: number) => {
    const unit = timeline!.units.find((u) => u.id === unitId)!
    const clips = unit.clips.map((c, i) => (i === idx && isImageClip(c) ? { ...c, seconds: Math.max(0.1, v) } : c))
    updateUnitClips(unitId, clips)
    void api.postEvent(slug!, { kind: 'clip_trimmed', unit: unitId, clip: clipRef(clips[idx]), field: 'seconds', value: v })
  }

  const addClip = (unitId: string, clip: api.Clip) => {
    const unit = timeline!.units.find((u) => u.id === unitId)!
    updateUnitClips(unitId, [...unit.clips, clip])
    void api.postEvent(slug!, { kind: 'clip_added', unit: unitId, clip: clipRef(clip) })
  }

  const save = async () => {
    if (!timeline || !slug) return
    setSaving(true)
    try {
      await api.putTimeline(slug, timeline)
      show(t('cut.saved'))
    } catch (e) {
      showError(e)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <StageBar stage="cut" done={!!cutDone} onDone={refresh} />
      {!cutDone && <p className="muted">{t('cut.no_timeline')}</p>}
      {cutDone && !timeline && (
        <div className="center-msg">
          <Spinner />
        </div>
      )}
      {cutDone && timeline && slug && (
        <>
          <p className="hint">{t('cut.hint')}</p>
          {timeline.units.map((u) => (
            <div key={u.id} className="card unit-row">
              <div className="row-between">
                <span className="badge badge-accent">{u.id}</span>
                <span className="small muted">{t('cut.estimated', { v: u.estimated_seconds.toFixed(1) })}</span>
              </div>
              <div className="clip-strip">
                {u.clips.map((c, idx) => (
                  <ClipCard
                    key={idx}
                    clip={c}
                    slug={slug}
                    isFirst={idx === 0}
                    isLast={idx === u.clips.length - 1}
                    onMove={(dir) => move(u.id, idx, dir)}
                    onDelete={() => del(u.id, idx)}
                    onInOut={(field, v) => inOut(u.id, idx, field, v)}
                    onSeconds={(v) => seconds(u.id, idx, v)}
                  />
                ))}
                <button className="btn btn-small" onClick={() => setAddingTo(u.id)}>
                  + {t('cut.add_from_candidates')}
                </button>
              </div>
            </div>
          ))}
          <button className="btn btn-primary" onClick={save} disabled={saving}>
            {t('cut.save_timeline')}
          </button>
          {addingTo && (
            <AddFromCandidates
              slug={slug}
              unitId={addingTo}
              candidates={candidates?.units.find((u) => u.unit_id === addingTo)}
              onAdd={(clip) => addClip(addingTo, clip)}
              onClose={() => setAddingTo(null)}
            />
          )}
        </>
      )}
    </div>
  )
}
