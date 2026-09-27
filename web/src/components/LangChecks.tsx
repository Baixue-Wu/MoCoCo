import { useI18n } from '../i18n'
import type { Lang } from '../api'

export function LangChecks({ value, onChange }: { value: Lang[]; onChange: (v: Lang[]) => void }) {
  const { t } = useI18n()
  const toggle = (l: Lang) => {
    if (value.includes(l)) onChange(value.filter((x) => x !== l))
    else onChange([...value, l])
  }
  return (
    <div className="checkbox-row">
      {(['zh', 'en'] as Lang[]).map((l) => (
        <label key={l}>
          <input type="checkbox" checked={value.includes(l)} onChange={() => toggle(l)} />
          {t(`newp.lang.${l}`)}
        </label>
      ))}
    </div>
  )
}
