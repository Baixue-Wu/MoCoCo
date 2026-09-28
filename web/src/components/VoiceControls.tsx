import { useEffect, useRef, useState } from 'react'
import * as api from '../api'
import { useI18n } from '../i18n'
import { useToast } from './Toast'
import { Spinner } from './Spinner'

const RATES: { value: string; labelKey: string }[] = [
  { value: '-10%', labelKey: 'setup.rate_slower' },
  { value: '+0%', labelKey: 'setup.rate_normal' },
  { value: '+10%', labelKey: 'setup.rate_faster' },
  { value: '+20%', labelKey: 'setup.rate_fastest' },
]

export function RateSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const { t } = useI18n()
  // the stored rate might not be one of the four canonical options (hand-edited project.json); keep it selectable.
  const options = RATES.some((r) => r.value === value) ? RATES : [{ value, labelKey: '' }, ...RATES]
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} style={{ maxWidth: 200 }}>
      {options.map((r) => (
        <option key={r.value} value={r.value}>
          {r.labelKey ? t(r.labelKey) : r.value}
        </option>
      ))}
    </select>
  )
}

export function VoiceSelect({
  lang,
  value,
  onChange,
}: {
  lang: string
  value: string
  onChange: (name: string) => void
}) {
  const { t } = useI18n()
  const { showError } = useToast()
  const [options, setOptions] = useState<api.VoiceOption[] | null>(null)

  useEffect(() => {
    let live = true
    api
      .listVoices(lang)
      .then((v) => {
        if (live) setOptions(v)
      })
      .catch(showError)
    return () => {
      live = false
    }
  }, [lang, showError])

  if (!options) {
    return <Spinner />
  }

  const known = options.find((o) => o.name === value)
  const groups: Record<string, api.VoiceOption[]> = {}
  for (const o of options) {
    const g = o.gender || 'other'
    ;(groups[g] ??= []).push(o)
  }
  const genderLabel = (g: string) =>
    g.toLowerCase() === 'female' ? t('setup.voice_gender_female') : g.toLowerCase() === 'male' ? t('setup.voice_gender_male') : t('setup.voice_gender_other')

  return (
    <select value={value} onChange={(e) => onChange(e.target.value)}>
      {!known && <option value={value}>{value}</option>}
      {Object.entries(groups).map(([g, list]) => (
        <optgroup key={g} label={genderLabel(g)}>
          {list.map((o) => (
            <option key={o.name} value={o.name}>
              {o.label}
            </option>
          ))}
        </optgroup>
      ))}
    </select>
  )
}

export function VoicePreviewButton({ lang, voice, rate }: { lang: string; voice: string; rate: string }) {
  const { t } = useI18n()
  const { showError } = useToast()
  const audioRef = useRef<HTMLAudioElement>(null)
  const [loading, setLoading] = useState(false)

  const play = () => {
    const audio = audioRef.current
    if (!audio || !voice) return
    setLoading(true)
    audio.src = api.voicePreviewUrl(voice, lang, rate)
    audio.oncanplay = () => setLoading(false)
    audio.onerror = () => {
      setLoading(false)
      showError(t('setup.preview'))
    }
    audio.play().catch(() => setLoading(false))
  }

  return (
    <>
      <button type="button" className="btn btn-small" onClick={play} disabled={loading || !voice}>
        {loading ? <Spinner /> : `▶ ${t('setup.preview')}`}
      </button>
      <audio ref={audioRef} hidden />
    </>
  )
}
