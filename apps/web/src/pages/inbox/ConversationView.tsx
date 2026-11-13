import { useEffect, useRef, useState } from 'react'
import { ArrowLeft, Bot, Check, Loader2, MessageSquare, Phone, UserPlus } from 'lucide-react'
import clsx from 'clsx'
import { Composer } from './Composer'
import { LeadDialog } from './LeadDialog'
import { ModeSwitch } from './ModeSwitch'
import { displayName, fmtClock, toUiMode, type Conversation, type Message, type UiMode } from './types'

export interface PendingMessage extends Message { failed?: boolean }

interface Props {
  conv: Conversation | null
  hasAny: boolean
  messages: PendingMessage[]
  loadingMessages: boolean
  onBack?: () => void
  onMode: (m: UiMode) => void
  onSend: (text: string) => Promise<boolean>
  onApproveDraft: (id: number) => Promise<void>
  onUseDraft: (text: string) => void
  draft: { text: string; n: number }
  onLeadCreated: (name: string) => void
  leadDone: boolean
}

export function ConversationView(p: Props) {
  const { conv } = p
  const listRef = useRef<HTMLDivElement>(null)
  const stick = useRef(true)
  const lastKey = useRef('')
  const [leadOpen, setLeadOpen] = useState(false)
  const [busyDraft, setBusyDraft] = useState<number | null>(null)

  // Yeni mesajda en alta kaydır (kullanıcı yukarı okuyorsa bölme; konuşma değişince hep in)
  useEffect(() => {
    const el = listRef.current
    if (!el) return
    const key = `${conv?.id}:${p.messages.length}:${p.messages[p.messages.length - 1]?.id}`
    if (key !== lastKey.current) {
      const changedConv = !lastKey.current.startsWith(`${conv?.id}:`)
      if (stick.current || changedConv) el.scrollTop = el.scrollHeight
      lastKey.current = key
    }
  }, [conv?.id, p.messages])

  if (!conv) {
    return (
      <section className="h-full grid place-items-center bg-os-panel border border-os-line rounded-[14px] text-os-muted">
        <div className="text-center">
          <MessageSquare className="w-12 h-12 mx-auto mb-3 opacity-40" aria-hidden="true" />
          <div className="text-[15px]">{p.hasAny ? 'Konuşma seçiniz' : 'Henüz konuşma yok'}</div>
        </div>
      </section>
    )
  }

  const mode = toUiMode(conv.ai_mode)

  return (
    <section aria-label="Konuşma" className="flex flex-col min-h-0 h-full bg-os-panel border border-os-line rounded-[14px] overflow-hidden">
      <header className="flex flex-wrap items-center gap-x-3 gap-y-2 px-3 sm:px-4 py-3 border-b border-os-line">
        {p.onBack && (
          <button type="button" onClick={p.onBack} className="grid place-items-center w-11 h-11 -ml-2 rounded-[10px] text-os-text2 hover:bg-os-raised" aria-label="Konuşma listesine dön">
            <ArrowLeft className="w-5 h-5" />
          </button>
        )}
        <div className="min-w-0 flex-1 basis-40">
          <h2 className="font-bold text-[16px] text-os-text truncate">{displayName(conv)}</h2>
          <div className="text-[13px] text-os-muted flex items-center gap-1.5"><Phone className="w-3.5 h-3.5" aria-hidden="true" />{conv.phone}</div>
        </div>
        <ModeSwitch mode={conv.ai_mode} onChange={p.onMode} />
        <button
          type="button"
          onClick={() => setLeadOpen(true)}
          disabled={p.leadDone}
          className="min-h-[44px] px-3.5 rounded-[10px] border border-os-line2 text-os-text2 text-[13px] font-semibold flex items-center gap-2 hover:bg-os-raised disabled:opacity-60"
        >
          {p.leadDone ? <Check className="w-4 h-4 text-os-ok" aria-hidden="true" /> : <UserPlus className="w-4 h-4" aria-hidden="true" />}
          {p.leadDone ? 'Lead oluşturuldu' : "Lead'e dönüştür"}
        </button>
      </header>

      <div
        ref={listRef}
        onScroll={(e) => { const el = e.currentTarget; stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120 }}
        className="flex-1 min-h-0 overflow-y-auto p-3 sm:p-4 space-y-3"
        role="log"
        aria-label="Mesajlar"
      >
        {p.loadingMessages && p.messages.length === 0 && <div className="text-sm text-os-muted">Mesajlar yükleniyor…</div>}
        {p.messages.map((m) => (
          <div key={m.id}>
            <Bubble m={m} />
            {m.direction === 'inbound' && m.ai_draft && !m.ai_auto_sent && (
              <div className="mt-2 ml-2 sm:ml-6 p-3 rounded-[10px] bg-os-bg border border-os-line2 max-w-[85%]">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-os-accent mb-1.5">
                  <Bot className="w-4 h-4" aria-hidden="true" /> JARVIS taslağı
                  {m.ai_confidence != null && <span className="text-os-muted font-normal">· güven %{Math.round(m.ai_confidence * 100)}</span>}
                </div>
                <div className="text-[14px] text-os-text2 whitespace-pre-wrap break-words mb-3">{m.ai_draft}</div>
                <div className="flex flex-wrap gap-2">
                  <button type="button" disabled={busyDraft !== null}
                    onClick={async () => { setBusyDraft(m.id); await p.onApproveDraft(m.id); setBusyDraft(null) }}
                    className="min-h-[44px] px-3.5 rounded-[10px] bg-os-accent text-os-onaccent text-[13px] font-semibold flex items-center gap-1.5 disabled:opacity-50">
                    {busyDraft === m.id ? <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" /> : <Check className="w-4 h-4" aria-hidden="true" />}
                    Onayla ve gönder
                  </button>
                  <button type="button" onClick={() => p.onUseDraft(m.ai_draft || '')}
                    className="min-h-[44px] px-3.5 rounded-[10px] border border-os-line2 text-os-text2 text-[13px] font-semibold hover:bg-os-raised">
                    Düzenle
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {mode === 'auto_reply' ? (
        <div className="p-3 border-t border-os-line flex flex-wrap items-center gap-3">
          <p className="flex-1 basis-48 text-[14px] text-os-text2 flex items-center gap-2">
            <Bot className="w-4 h-4 text-os-accent shrink-0" aria-hidden="true" /> Bu konuşmayı JARVIS yanıtlıyor.
          </p>
          <button type="button" onClick={() => p.onMode('manual')}
            className="min-h-[44px] px-4 rounded-[10px] bg-os-accent text-os-onaccent font-semibold">
            Konuşmayı devral
          </button>
        </div>
      ) : (
        <Composer
          key={`${conv.id}:${p.draft.n}`}
          initial={p.draft.text}
          onSend={p.onSend}
          hint={mode === 'auto_draft' ? 'Taslak modu: JARVIS taslak hazırlar, onayınla gider. İstersen kendin de yazabilirsin.' : undefined}
        />
      )}

      {leadOpen && (
        <LeadDialog conv={conv} onClose={() => setLeadOpen(false)} onCreated={(n) => { setLeadOpen(false); p.onLeadCreated(n) }} />
      )}
    </section>
  )
}

function Bubble({ m }: { m: PendingMessage }) {
  const inbound = m.direction === 'inbound'
  const who = inbound ? '' : m.sent_by === 'ai' ? 'JARVIS · ' : 'Siz · '
  const sending = m.id < 0 && !m.failed
  return (
    <div className={clsx('flex', inbound ? 'justify-start' : 'justify-end')}>
      <div className="max-w-[85%] sm:max-w-[70%] min-w-0">
        <div className={clsx(
          'rounded-2xl px-4 py-2.5 border',
          inbound ? 'bg-os-inbg border-os-inline text-os-text rounded-bl-md' : 'bg-os-outbg border-os-outline text-os-outtext rounded-br-md',
          sending && 'opacity-70',
        )}>
          <div className="text-[15px] whitespace-pre-wrap break-words [overflow-wrap:anywhere]">{m.content}</div>
        </div>
        <div className={clsx('mt-1 px-1 text-xs text-os-muted', inbound ? 'text-left' : 'text-right')}>
          {who}{fmtClock(m.created_at)}{sending && ' · gönderiliyor…'}
        </div>
      </div>
    </div>
  )
}
