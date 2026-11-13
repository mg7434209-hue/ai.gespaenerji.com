import { useRef, useState } from 'react'
import { Loader2, Send } from 'lucide-react'

/** Mesaj kutusu: Enter gönderir, Shift+Enter satır ekler, boş mesaj gönderilmez.
 *  `onSend` false dönerse (hata) metin kutuya geri konur. */
export function Composer({ onSend, hint, initial = '' }: { onSend: (text: string) => Promise<boolean>; hint?: string; initial?: string }) {
  const [text, setText] = useState(initial)
  const [busy, setBusy] = useState(false)
  const ref = useRef<HTMLTextAreaElement>(null)

  async function submit() {
    const body = text.trim()
    if (!body || busy) return
    setText('')
    setBusy(true)
    const ok = await onSend(body)
    setBusy(false)
    if (!ok) setText((cur) => (cur ? cur : body))
    ref.current?.focus()
  }

  return (
    <div className="p-3 border-t border-os-line">
      {hint && <div className="text-xs text-os-muted mb-2">{hint}</div>}
      <form onSubmit={(e) => { e.preventDefault(); void submit() }} className="flex gap-2 items-end">
        <textarea
          ref={ref}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void submit() }
          }}
          rows={2}
          aria-label="Mesaj"
          placeholder="Mesaj yaz… (Enter gönderir, Shift+Enter satır ekler)"
          className="flex-1 min-w-0 resize-none rounded-[10px] bg-os-bg border border-os-line px-3.5 py-2.5 text-[15px] text-os-text placeholder:text-os-muted outline-none focus:border-os-accent"
        />
        <button
          type="submit"
          disabled={busy || !text.trim()}
          className="min-h-[44px] px-4 rounded-[10px] bg-os-accent text-os-onaccent font-semibold flex items-center gap-2 disabled:opacity-50"
        >
          {busy ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : <Send className="w-4 h-4" aria-hidden="true" />}
          Gönder
        </button>
      </form>
    </div>
  )
}
