import type { ReactNode } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { useI18n } from '../i18n'
import { STEP_ORDER } from '../state/steps'

export function ExampleWorkflow({ title, intro, steps, children }: {
  title: string
  intro: string
  steps?: { path: string; label: string }[]
  children: ReactNode
}) {
  const { t } = useI18n()
  const navigation = steps ?? STEP_ORDER.map(step => ({ path: step === 'setup' ? '' : step, label: t(`step.${step}`) }))
  return <div>
    <Link to="/" className="small">← {t('common.back')}</Link>
    <div className="row-between example-project-heading" style={{ flexWrap: 'wrap', gap: 12 }}>
      <div style={{ flex: '1 1 260px', minWidth: 0 }}><h1>{title}</h1><span className="badge badge-accent">{t('example.read_only')}</span></div>
      <Link to="/" className="btn">{t('example.try')}</Link>
    </div>
    <p className="muted example-project-note">{intro}</p>
    <div className="wizard">
      <nav className="wizard-nav" aria-label={t('example.workflow')}>
        {navigation.map(step => <NavLink key={step.path} to={step.path || '.'} end className={({ isActive }) => isActive ? 'active' : ''}><span>{step.label}</span><span className="dot done" /></NavLink>)}
      </nav>
      <div style={{ minWidth: 0 }}>{children}</div>
    </div>
  </div>
}
