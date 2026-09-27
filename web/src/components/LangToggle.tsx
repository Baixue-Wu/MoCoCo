import { useI18n } from '../i18n'

export function LangToggle() {
  const { lang, setLang } = useI18n()
  return (
    <div className="lang-toggle">
      <button className={lang === 'en' ? 'active' : ''} onClick={() => setLang('en')}>
        English
      </button>
      <button className={lang === 'zh' ? 'active' : ''} onClick={() => setLang('zh')}>
        中文
      </button>
    </div>
  )
}
