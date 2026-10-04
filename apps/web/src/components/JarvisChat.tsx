import { useEffect, useRef, useState } from 'react'
import { Bot, Loader2, Plus, Send } from 'lucide-react'
import clsx from 'clsx'
import { api } from '@/lib/api'
import type { JarvisChatResponse, JarvisConversation, JarvisMessage } from '@/types'

// Hangi verinin okunduğunu gösteren rozetler (araç adı → etiket)
const TOOL_LABELS: Record<string, string> = {
  get_agenda: '📅 ajanda',
  list_deadlines: '⏱ süreler',
  list_matters: '📁 dosyalar',
  get_matter: '📁 dosya',
  list_workspaces: '🗂 workspace',
  list_leads: '👤 lead',
  inbox_summary: '💬 WhatsApp',
  site_overview: '🌐 siteler',
  site_orders: '🛒 siparişler',
  site_catalog: '📦 katalog',
  site_questions: '❓ soru-cevap',
}

const SUGGESTIONS = ['Siteler bugün nasıl?', 'Yeni sipariş var mı?', 'Hangi ürünlerde sorun var?']

/** Ana sayfadaki komuta kutusu — JARVIS gerçek veriden cevap verir (Faz 1: yalnız okur). */
export function JarvisChat() {
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [messages, setMessages] = useState<JarvisMessage[]>([])
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [configured, setConfigured] = useState(true)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.get<{ configured: boolean }>('/jarvis/status')
      .then(({ data }) => setConfigured(data.configured))
      .catch(() => {})
    api.get<JarvisConversation | null>('/jarvis/conversations/latest', { params: { channel: 'web' } })
      .then(({ data }) => {
        if (data) {
          setConversationId(data.id)
          setMessages(data.messages)
        }
      })
      .catch(() => {})
  }, [])

  // Yalnız kutunun içi kayar; sayfa zıplamaz
  useEffect(() => {
    const el = listRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages.length, sending])

  async function ask(body: string) {
    body = body.trim()
    if (!body || sending) return
    setSending(true)
    setError(null)
    setText('')
    const temp: JarvisMessage = {
      id: -Date.now(), role: 'user', text: body, tools: [], created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, temp])
    try {
      const { data } = await api.post<JarvisChatResponse>('/jarvis/chat', {
        message: body,
        conversation_id: conversationId,
      })
      setConversationId(data.conversation_id)
      setMessages((prev) => [
        ...prev,
        { id: Date.now(), role: 'assistant', text: data.reply, tools: data.tools, created_at: new Date().toISOString() },
      ])
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'JARVIS yanıt veremedi.')
      setMessages((prev) => prev.filter((m) => m.id !== temp.id))
      setText(body)
    } finally {
      setSending(false)
    }
  }

  function newChat() {
    setConversationId(null)
    setMessages([])
    setError(null)
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-brand-400" />
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">JARVIS</h2>
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">yalnız okur</span>
        </div>
        {messages.length > 0 && (
          <button onClick={newChat} className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1">
            <Plus className="w-3 h-3" /> Yeni sohbet
          </button>
        )}
      </div>

      {!configured && (
        <p className="text-sm text-amber-400 mb-3">
          JARVIS kapalı: sunucuda ANTHROPIC_API_KEY tanımlı değil.
        </p>
      )}

      {messages.length === 0 ? (
        <div className="flex flex-wrap gap-2 mb-4">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => ask(s)}
              disabled={sending || !configured}
              className="text-sm px-3 py-1.5 rounded-full border border-slate-700 text-slate-300 hover:border-brand-500/50 hover:text-slate-100 transition-colors disabled:opacity-50"
            >
              {s}
            </button>
          ))}
        </div>
      ) : (
        <div ref={listRef} className="space-y-3 max-h-[26rem] overflow-y-auto pr-1 mb-4">
          {messages.map((m) => (
            <div key={m.id} className={clsx('flex flex-col', m.role === 'user' ? 'items-end' : 'items-start')}>
              <div
                className={clsx(
                  'max-w-[90%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap break-words',
                  m.role === 'user'
                    ? 'bg-brand-500/10 text-slate-100 rounded-br-sm'
                    : 'bg-slate-800/60 text-slate-200 rounded-bl-sm',
                )}
              >
                {m.text}
              </div>
              {m.role === 'assistant' && m.tools.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1">
                  {[...new Set(m.tools)].map((t) => (
                    <span key={t} className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800/80 text-slate-500">
                      {TOOL_LABELS[t] || t}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
          {sending && (
            <div className="flex justify-start">
              <div className="bg-slate-800/60 rounded-2xl rounded-bl-sm px-4 py-2.5 flex items-center gap-2 text-xs text-slate-400">
                <Loader2 className="w-4 h-4 animate-spin text-brand-400" /> veriye bakıyor…
              </div>
            </div>
          )}
        </div>
      )}

      {error && <p className="text-sm text-red-400 mb-3">{error}</p>}

      <form onSubmit={(e) => { e.preventDefault(); ask(text) }} className="flex gap-2">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Bir şey sor: dünden beri sipariş var mı?"
          className="input flex-1"
          disabled={sending || !configured}
          maxLength={4000}
        />
        <button type="submit" disabled={sending || !configured || !text.trim()} className="btn-primary px-4" aria-label="Gönder">
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  )
}
