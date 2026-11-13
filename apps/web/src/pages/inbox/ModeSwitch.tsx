import clsx from 'clsx'
import { MODE_LABEL, toUiMode, type UiMode } from './types'

const ORDER: UiMode[] = ['auto_reply', 'auto_draft', 'manual']

/** Yanıt modu anahtarı: Tam Otomatik | Taslak | Manuel. */
export function ModeSwitch({ mode, onChange, disabled }: { mode: string; onChange: (m: UiMode) => void; disabled?: boolean }) {
  const current = toUiMode(mode)
  return (
    <div role="radiogroup" aria-label="Yanıt modu" className="inline-flex p-0.5 rounded-[10px] bg-os-bg border border-os-line">
      {ORDER.map((m) => (
        <button
          key={m}
          type="button"
          role="radio"
          aria-checked={current === m}
          disabled={disabled}
          onClick={() => current !== m && onChange(m)}
          className={clsx(
            'min-h-[44px] px-3.5 rounded-[8px] text-[13px] font-semibold whitespace-nowrap transition-colors disabled:opacity-50',
            current === m ? 'bg-os-accent text-os-onaccent' : 'text-os-text2 hover:bg-os-raised',
          )}
        >
          {MODE_LABEL[m]}
        </button>
      ))}
    </div>
  )
}
