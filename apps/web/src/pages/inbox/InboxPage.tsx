import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from '@/lib/api'
import { useShellSearch } from '@/components/layout/shellContext'
import { ConversationList, type Filter } from './ConversationList'
import { ConversationView, type PendingMessage } from './ConversationView'
import { displayName, norm, type Conversation, type Message, type UiMode } from './types'

function useMediaQuery(query: string) {
  const [match, setMatch] = useState(() => window.matchMedia(query).matches)
  useEffect(() => {
    const mq = window.matchMedia(query)
    const on = () => setMatch(mq.matches)
    on()
    mq.addEventListener('change', on)
    return () => mq.removeEventListener('change', on)
  }, [query])
  return match
}

export function InboxPage() {
  const search = useShellSearch()
  const wide = useMediaQuery('(min-width: 900px)')
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [filter, setFilter] = useState<Filter>('all')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [view, setView] = useState<'list' | 'chat'>('list')
  const [messages, setMessages] = useState<PendingMessage[]>([])
  const [loadingMsgs, setLoadingMsgs] = useState(false)
  const [draft, setDraft] = useState({ text: '', n: 0 })
  const [leadDone, setLeadDone] = useState<Set<number>>(new Set())
  const [toast, setToast] = useState<{ text: string; kind: 'error' | 'ok' } | null>(null)
  const modeLock = useRef(new Map<number, string>())   // istek sürerken sunucu yanıtı yerel değeri ezmesin

  const notify = useCallback((text: string, kind: 'error' | 'ok' = 'error') => {
    setToast({ text, kind })
    window.setTimeout(() => setToast((t) => (t && t.text === text ? null : t)), 4000)
  }, [])

  // ── Konuşma listesi ──
  const loadConversations = useCallback(async () => {
    try {
      const { data } = await api.get<Conversation[]>('/whatsapp/conversations', { params: { limit: 100 } })
      setConversations(data.map((c) => (modeLock.current.has(c.id) ? { ...c, ai_mode: modeLock.current.get(c.id)! } : c)))
      setStatus('ready')
    } catch {
      setStatus((s) => (s === 'ready' ? 'ready' : 'error'))   // ilk yükleme düşerse hata; sonraki yenilemeler sessiz
    }
  }, [])

  useEffect(() => {
    loadConversations()
    const t = setInterval(loadConversations, 10000)
    return () => clearInterval(t)
  }, [loadConversations])

  // Geniş ekranda ilk konuşma otomatik seçilir (dar ekranda liste önce görünür)
  useEffect(() => {
    if (wide && selectedId === null && conversations.length > 0) setSelectedId(conversations[0].id)
  }, [wide, selectedId, conversations])

  // ── Seçili konuşmanın mesajları ──
  const loadMessages = useCallback(async (id: number) => {
    const { data } = await api.get<Message[]>(`/whatsapp/conversations/${id}/messages`)
    setMessages((prev) => [...data, ...prev.filter((m) => m.id < 0)])   // gönderilmekte olanlar kalsın
  }, [])

  useEffect(() => {
    if (selectedId === null) return
    let alive = true
    setMessages([])
    setLoadingMsgs(true)
    const run = (first: boolean) => loadMessages(selectedId)
      .then(() => { if (alive && first) { setLoadingMsgs(false); loadConversations() } })   // açınca sunucu okundu işaretler
      .catch(() => { if (alive && first) setLoadingMsgs(false) })
    run(true)
    const t = setInterval(() => run(false), 5000)
    return () => { alive = false; clearInterval(t) }
  }, [selectedId, loadMessages, loadConversations])

  const selected = conversations.find((c) => c.id === selectedId) ?? null

  // ── Süzme ──
  const counts = useMemo(() => ({
    all: conversations.length,
    urgent: conversations.filter((c) => c.needs_attention).length,
    unread: conversations.filter((c) => c.unread_count > 0).length,
  }), [conversations])

  const q = norm(search.trim())
  const visible = useMemo(() => conversations.filter((c) => {
    if (filter === 'urgent' && !c.needs_attention) return false
    if (filter === 'unread' && c.unread_count === 0) return false
    return !q || norm(`${displayName(c)} ${c.phone} ${c.last_message_preview || ''}`).includes(q)
  }), [conversations, filter, q])

  // ── Eylemler (iyimser; hata olursa geri alınır) ──
  async function changeMode(mode: UiMode) {
    if (!selected) return
    const id = selected.id, prev = selected.ai_mode
    modeLock.current.set(id, mode)
    setConversations((cs) => cs.map((c) => (c.id === id ? { ...c, ai_mode: mode } : c)))
    try {
      await api.patch(`/whatsapp/conversations/${id}`, { ai_mode: mode })
    } catch {
      setConversations((cs) => cs.map((c) => (c.id === id ? { ...c, ai_mode: prev } : c)))
      notify('Yanıt modu değiştirilemedi. Tekrar dene.')
    } finally {
      modeLock.current.delete(id)
    }
  }

  async function send(text: string): Promise<boolean> {
    if (!selected) return false
    const id = selected.id
    const temp: PendingMessage = {
      id: -Date.now(), direction: 'outbound', content_type: 'text', content: text,
      ai_auto_sent: false, status: 'sending', sent_by: 'user', created_at: new Date().toISOString(),
    }
    setMessages((m) => [...m, temp])
    try {
      await api.post(`/whatsapp/conversations/${id}/send`, { body: text })
      const { data } = await api.get<Message[]>(`/whatsapp/conversations/${id}/messages`)
      setMessages((prev) => [...data, ...prev.filter((m) => m.id < 0 && m.id !== temp.id)])
      loadConversations()
      return true
    } catch {
      setMessages((m) => m.filter((x) => x.id !== temp.id))
      notify('Mesaj gönderilemedi. Metin kutuda duruyor, tekrar dene.')
      return false
    }
  }

  async function approveDraft(msgId: number) {
    if (!selected) return
    try {
      await api.post(`/whatsapp/messages/${msgId}/approve-draft`)
      await loadMessages(selected.id)
      loadConversations()
    } catch {
      notify('Taslak gönderilemedi. Tekrar dene.')
    }
  }

  const select = (id: number) => {
    if (id !== selectedId) { setSelectedId(id); setDraft({ text: '', n: draft.n + 1 }) }
    setView('chat')
  }

  return (
    <div className="h-full min-h-0 flex gap-4 p-3 md:p-4 relative">
      {(wide || view === 'list') && (
        <div className={wide ? 'w-[340px] shrink-0 min-h-0' : 'flex-1 min-w-0 min-h-0'}>
          <ConversationList
            conversations={visible} counts={counts} filter={filter} onFilter={setFilter}
            selectedId={selectedId} onSelect={select} status={status}
            onRetry={() => { setStatus('loading'); loadConversations() }} searching={q.length > 0}
          />
        </div>
      )}
      {(wide || view === 'chat') && (
        <div className="flex-1 min-w-0 min-h-0">
          <ConversationView
            conv={selected} hasAny={conversations.length > 0} messages={messages} loadingMessages={loadingMsgs}
            onBack={wide ? undefined : () => setView('list')}
            onMode={changeMode} onSend={send} onApproveDraft={approveDraft}
            onUseDraft={(text) => setDraft((d) => ({ text, n: d.n + 1 }))} draft={draft}
            leadDone={selected ? leadDone.has(selected.id) : false}
            onLeadCreated={(name) => {
              if (selected) setLeadDone((s) => new Set(s).add(selected.id))
              notify(`${name} lead olarak eklendi.`, 'ok')
            }}
          />
        </div>
      )}
      {toast && (
        <div
          role={toast.kind === 'error' ? 'alert' : 'status'}
          className={`fixed bottom-4 left-1/2 -translate-x-1/2 z-[70] max-w-[calc(100vw-2rem)] px-4 py-3 rounded-[10px] border text-[14px] ${
            toast.kind === 'error' ? 'bg-os-urgentbg border-os-urgentfg/40 text-os-urgentfg' : 'bg-os-panel border-os-line2 text-os-ok'}`}
        >
          {toast.text}
        </div>
      )}
    </div>
  )
}
