import { useEffect, useState } from 'react'
import * as api from '../../api'
import { useI18n } from '../../i18n'
import { useToast } from '../../components/Toast'
import { useProject } from '../../state/ProjectContext'
import { StageBar } from '../../components/StageBar'
import { stepDone } from '../../state/steps'

function CostSummary() {
  const { t } = useI18n()
  const { detail } = useProject()
  const { showError } = useToast()
  const [summary, setSummary] = useState<{ n: number; cost: number } | null>(null)

  useEffect(() => {
    api
      .getEvents(detail!.slug)
      .then((events) => {
        const calls = events.filter((e) => e.kind === 'llm_call')
        const cost = calls.reduce((sum, e) => sum + (Number(e.cost_usd) || 0), 0)
        setSummary({ n: calls.length, cost })
      })
      .catch(showError)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail!.slug])

  if (!summary) return null

  return (
    <div className="card section">
      <h2>{t('export.cost_summary')}</h2>
      <p>{t('export.cost_total', { n: summary.n, cost: summary.cost.toFixed(3) })}</p>
    </div>
  )
}

function OutputLang({ lang }: { lang: string }) {
  const { t } = useI18n()
  const { detail } = useProject()
  const slug = detail!.slug
  const done = detail!.status.render[lang]

  return (
    <div className="card section">
      <h2>{t(`newp.lang.${lang}`)}</h2>
      {done ? (
        <>
          <video controls src={api.mediaOutput(slug, lang)} />
          <a className="btn btn-small" style={{ marginTop: 8 }} href={api.mediaOutput(slug, lang)} download>
            {t('common.download')}
          </a>
        </>
      ) : (
        <p className="muted">{t('export.no_output')}</p>
      )}
    </div>
  )
}

export function ExportStep() {
  const { detail, refresh } = useProject()
  if (!detail) return null
  const langs = detail.settings.voice_langs

  return (
    <div>
      <StageBar stage="render" done={stepDone('export', detail.status)} onDone={refresh} />
      {langs.map((l) => (
        <OutputLang key={l} lang={l} />
      ))}
      <CostSummary />
    </div>
  )
}
