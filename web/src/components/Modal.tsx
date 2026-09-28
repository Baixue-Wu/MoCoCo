import type { ReactNode } from 'react'
import { useI18n } from '../i18n'

export function Modal({ onClose, children }: { onClose: () => void; children: ReactNode }) {
  const { t } = useI18n()
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-body" onClick={(e) => e.stopPropagation()}>
        <div className="row-between" style={{ marginBottom: 10 }}>
          <div />
          <button className="btn btn-small" onClick={onClose}>
            {t('common.close')}
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
