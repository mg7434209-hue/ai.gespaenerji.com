import { useEffect, useRef, useState } from 'react'
import { Bot, Loader2, Plus, Send, Mic, Square, Volume2, VolumeX } from 'lucide-react'
import clsx from 'clsx'
import { useSpeech } from '../useSpeech'
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
}

const SUGGESTIONS = ['Bu hafta neyim var?', 'Geciken süre var mı?', 'Teklif bekleyen lead\'ler?']

/** Ana sayfadaki komuta kutusu — JARVIS gerçek veriden cevap verir (Faz 1: yalnız okur). */
export function JarvisChat({ fullPage = false }: { fullPage?: boolean }) {
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [messages, setMessages] = useState<JarvisMessage[]>([])
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [configured, setConfigured] = useState(true)
  const [voiceEnabled, setVoiceEnabled] = useState(false)
  const speech = useSpeech(value => setText(prev => (prev + ' ' + value).trim().slice(0, 4000)))
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
    speech.stopListening()
    speech.stopSpeaking()
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
      if (voiceEnabled) speech.speak(data.reply)
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
    speech.stopListening()
    speech.stopSpeaking()
    setConversationId(null)
    setMessages([])
    setError(null)
  }

  return (
    <div className={clsx("card", fullPage && "jarvis-full flex flex-col")}>
      <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
        <div className="flex items-center gap-2">
          <Bot className="w-5 h-5 text-brand-400" />
          <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">JARVIS</h2>
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">yalnız okur</span>
        </div>
        <button type="button" onClick={() => { setVoiceEnabled(!voiceEnabled); speech.stopSpeaking() }} disabled={!speech.canSpeak} aria-pressed={voiceEnabled} className="text-sm min-h-11 flex items-center gap-2 text-slate-300 disabled:opacity-50">{voiceEnabled ? <Volume2 className="w-5 h-5" /> : <VolumeX className="w-5 h-5" />}Sesli yanıt {voiceEnabled ? "açık" : "kapalı"}</button>
        {messages.length > 0 && (
          <button onClick={newChat} disabled={sending} className="text-xs text-brand-400 hover:text-brand-300 flex items-center gap-1">
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
        <div ref={listRef} className={clsx("space-y-3 overflow-y-auto pr-1 mb-4 min-h-0", fullPage ? "flex-1" : "max-h-[26rem]")} role="log" aria-label="Sohbet mesajları" aria-live="polite">
          {messages.map((m) => (
            <div key={m.id} className={clsx('flex flex-col', m.role === 'user' ? 'items-end' : 'items-start')}>
              <div
                className={clsx(
                  'max-w-[90%] rounded-2xl px-4 py-2.5 text-base leading-relaxed whitespace-pre-wrap break-words [overflow-wrap:anywhere]',
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

      {(error || speech.error) && <p role="alert" className="text-sm text-red-400 mb-3">{error || speech.error}</p>}
      {speech.listening && <p role="status" className="text-sm text-brand-400 mb-3">Dinliyorum… Konuşmanız mesaj kutusuna yazılacak.</p>}
      {speech.speaking && <button type="button" onClick={speech.stopSpeaking} className="text-sm text-brand-400 min-h-11">Sesli okumayı durdur</button>}

      <form onSubmit={(e) => { e.preventDefault(); ask(text) }} className={clsx("flex gap-2", fullPage && "mt-auto")}>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Bir şey sor: bu hafta neyim var?"
          aria-label="JARVIS mesajı" className="input flex-1 min-w-0 text-base"
          disabled={sending || !configured}
          maxLength={4000}
        />
        <button type="button" onClick={speech.toggleListening} disabled={sending || !configured} aria-label={speech.listening ? "Dinlemeyi durdur" : "Mikrofonla yazdır"} aria-pressed={speech.listening} className="shrink-0 min-w-11 min-h-11 rounded-lg border border-slate-700 text-brand-400 flex items-center justify-center">{speech.listening ? <Square className="w-5 h-5" /> : <Mic className="w-5 h-5" />}</button>
        <button type="submit" disabled={sending || !configured || !text.trim()} className="btn-primary px-4" aria-label="Gönder">
          <Send className="w-4 h-4" />
        </button>
      </form>
      <p className="text-xs text-slate-400 leading-relaxed mt-3">Mikrofona basın, konuşun ve Gönder’e dokunun. Ses desteği tarayıcıya göre değişir. {!speech.supported && "Alternatif: telefon klavyenizin mikrofonunu kullanın."}</p>
    </div>
  )
}
