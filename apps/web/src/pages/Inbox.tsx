import { useEffect, useState } from 'react'
import { MessageSquare, Phone, AlertCircle, Bot, User, Send, Check, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { api } from '@/lib/api'

interface Conversation {
  id: number
  phone: string
  contact_name?: string
  profile_name?: string
  last_message_at: string
  last_message_preview?: string
  unread_count: number
  ai_mode: string
  is_vip: boolean
  needs_attention: boolean
  tags?: string[]
}

interface Message {
  id: number
  direction: 'inbound' | 'outbound'
  content_type: string
  content: string
  media_url?: string
  ai_intent?: string
  ai_sentiment?: string
  ai_confidence?: number
  ai_draft?: string
  ai_auto_sent: boolean
  status: string
  sent_by: string
  created_at: string
}

const AI_MODE_LABELS: Record<string, string> = {
  auto_reply: 'Tam Otomatik',
  auto_draft: 'Taslak + Onay',
  manual: 'Sadece Manuel',
  paused: 'AI Kapalı',
}

const INTENT_COLORS: Record<string, string> = {
  solar_teklif_talep: 'bg-amber-500/10 text-amber-400',
  modem_kurulum: 'bg-blue-500/10 text-blue-400',
  fiyat_araligi_sor: 'bg-purple-500/10 text-purple-400',
  selam: 'bg-green-500/10 text-green-400',
  tesekkur: 'bg-green-500/10 text-green-400',
  sikayet: 'bg-red-500/10 text-red-400',
  acil_ariza: 'bg-red-500/10 text-red-400',
}

export function Inbox() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [filter, setFilter] = useState<'all' | 'attention'>('all')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [replyText, setReplyText] = useState('')

  // Konuşmaları yükle
  async function loadConversations() {
    try {
      const params: any = { limit: 100 }
      if (filter === 'attention') params.needs_attention = true
      const { data } = await api.get<Conversation[]>('/whatsapp/conversations', { params })
      setConversations(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadConversations()
    const interval = setInterval(loadConversations, 10000) // 10 sn'de bir yenile
    return () => clearInterval(interval)
  }, [filter])

  // Seçili konuşmanın mesajlarını yükle
  async function loadMessages(convId: number) {
    const { data } = await api.get<Message[]>(`/whatsapp/conversations/${convId}/messages`)
    setMessages(data)
  }

  useEffect(() => {
    if (selectedId) {
      loadMessages(selectedId)
      const interval = setInterval(() => loadMessages(selectedId), 5000)
      return () => clearInterval(interval)
    }
  }, [selectedId])

  async function sendReply(text?: string) {
    if (!selectedId) return
    const body = text ?? replyText
    if (!body.trim()) return

    setSending(true)
    try {
      await api.post(`/whatsapp/conversations/${selectedId}/send`, { body })
      setReplyText('')
      await loadMessages(selectedId)
      await loadConversations()
    } finally {
      setSending(false)
    }
  }

  async function approveDraft(msgId: number) {
    setSending(true)
    try {
      await api.post(`/whatsapp/messages/${msgId}/approve-draft`)
      if (selectedId) await loadMessages(selectedId)
      await loadConversations()
    } finally {
      setSending(false)
    }
  }

  const selectedConv = conversations.find(c => c.id === selectedId)

  return (
    <div className="h-[calc(100vh-4rem)] flex gap-4 -m-8 p-4">
      {/* Sol: Konuşma listesi */}
      <div className="w-80 bg-slate-900/60 border border-slate-800 rounded-xl flex flex-col">
        <div className="p-4 border-b border-slate-800">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-bold text-slate-100 flex items-center gap-2">
              <MessageSquare className="w-5 h-5" />
              Inbox
            </h2>
          </div>
          <div className="flex gap-2 text-xs">
            <button
              onClick={() => setFilter('all')}
              className={clsx(
                'px-3 py-1.5 rounded-lg font-medium transition',
                filter === 'all' ? 'bg-brand-500 text-slate-950' : 'bg-slate-800 text-slate-400'
              )}
            >
              Tümü ({conversations.length})
            </button>
            <button
              onClick={() => setFilter('attention')}
              className={clsx(
                'px-3 py-1.5 rounded-lg font-medium transition',
                filter === 'attention' ? 'bg-red-500 text-white' : 'bg-slate-800 text-slate-400'
              )}
            >
              Acil
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="p-4 text-slate-500 text-sm">Yükleniyor...</div>
          ) : conversations.length === 0 ? (
            <div className="p-6 text-center">
              <MessageSquare className="w-12 h-12 text-slate-700 mx-auto mb-2" />
              <div className="text-sm text-slate-500">Henüz konuşma yok</div>
              <div className="text-xs text-slate-600 mt-1">
                WhatsApp entegrasyonu aktif olduğunda mesajlar burada görünür
              </div>
            </div>
          ) : (
            conversations.map(conv => (
              <button
                key={conv.id}
                onClick={() => setSelectedId(conv.id)}
                className={clsx(
                  'w-full text-left p-3 border-b border-slate-800/50 hover:bg-slate-800/30 transition',
                  selectedId === conv.id && 'bg-slate-800/50'
                )}
              >
                <div className="flex items-start justify-between mb-1">
                  <div className="font-medium text-slate-100 text-sm truncate flex items-center gap-1.5">
                    {conv.needs_attention && <AlertCircle className="w-3.5 h-3.5 text-red-400" />}
                    {conv.contact_name || conv.profile_name || conv.phone}
                  </div>
                  {conv.unread_count > 0 && (
                    <span className="bg-brand-500 text-slate-950 text-xs font-bold px-1.5 py-0.5 rounded-full">
                      {conv.unread_count}
                    </span>
                  )}
                </div>
                <div className="text-xs text-slate-400 truncate mb-1">
                  {conv.last_message_preview || '—'}
                </div>
                <div className="flex items-center gap-1.5 text-[10px]">
                  <span className="text-slate-600">{conv.phone}</span>
                  {conv.ai_mode !== 'auto_draft' && (
                    <span className="bg-slate-800 text-slate-500 px-1.5 rounded">
                      {AI_MODE_LABELS[conv.ai_mode]}
                    </span>
                  )}
                </div>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Sağ: Konuşma detayı */}
      <div className="flex-1 bg-slate-900/60 border border-slate-800 rounded-xl flex flex-col">
        {!selectedConv ? (
          <div className="flex-1 flex items-center justify-center text-slate-500">
            <div className="text-center">
              <MessageSquare className="w-16 h-16 mx-auto mb-3 opacity-30" />
              <div>Konuşma seçiniz</div>
            </div>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <div>
                <div className="font-bold text-slate-100">
                  {selectedConv.contact_name || selectedConv.profile_name || selectedConv.phone}
                </div>
                <div className="text-xs text-slate-400 flex items-center gap-1">
                  <Phone className="w-3 h-3" />
                  {selectedConv.phone}
                </div>
              </div>
              <div className="text-xs bg-slate-800 text-slate-400 px-2 py-1 rounded">
                {AI_MODE_LABELS[selectedConv.ai_mode]}
              </div>
            </div>

            {/* Mesajlar */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {messages.map(msg => (
                <div key={msg.id}>
                  <MessageBubble message={msg} />
                  {/* AI taslak göster (inbound için, henüz cevap yazılmamışsa) */}
                  {msg.direction === 'inbound' && msg.ai_draft && !msg.ai_auto_sent && (
                    <AIDraftCard
                      message={msg}
                      onApprove={() => approveDraft(msg.id)}
                      onReject={() => setReplyText(msg.ai_draft || '')}
                      loading={sending}
                    />
                  )}
                </div>
              ))}
            </div>

            {/* Cevap kutusu */}
            <div className="p-4 border-t border-slate-800">
              <div className="flex gap-2">
                <textarea
                  value={replyText}
                  onChange={e => setReplyText(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      sendReply()
                    }
                  }}
                  placeholder="Cevap yaz... (Enter: gönder, Shift+Enter: satır)"
                  className="input flex-1 min-h-[60px] resize-none"
                />
                <button
                  onClick={() => sendReply()}
                  disabled={sending || !replyText.trim()}
                  className="btn-primary flex items-center gap-2"
                >
                  {sending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                  Gönder
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function MessageBubble({ message }: { message: Message }) {
  const isInbound = message.direction === 'inbound'
  const isAI = message.sent_by === 'ai'
  return (
    <div className={clsx('flex', isInbound ? 'justify-start' : 'justify-end')}>
      <div className="max-w-[70%]">
        <div
          className={clsx(
            'rounded-2xl px-4 py-2.5',
            isInbound
              ? 'bg-slate-800 text-slate-100 rounded-bl-sm'
              : isAI
              ? 'bg-purple-500/20 border border-purple-500/30 text-slate-100 rounded-br-sm'
              : 'bg-brand-500 text-slate-950 rounded-br-sm'
          )}
        >
          <div className="text-sm whitespace-pre-wrap break-words">{message.content}</div>
        </div>
        <div className="flex items-center gap-2 mt-1 px-2 text-[10px] text-slate-500">
          {isAI && <Bot className="w-3 h-3 text-purple-400" />}
          {!isAI && !isInbound && <User className="w-3 h-3" />}
          <span>{new Date(message.created_at).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}</span>
          {!isInbound && <span>· {message.status}</span>}
          {message.ai_intent && (
            <span className={clsx('px-1.5 rounded', INTENT_COLORS[message.ai_intent] || 'bg-slate-700 text-slate-400')}>
              {message.ai_intent}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

function AIDraftCard({
  message,
  onApprove,
  onReject,
  loading,
}: {
  message: Message
  onApprove: () => void
  onReject: () => void
  loading: boolean
}) {
  return (
    <div className="mt-2 ml-4 p-3 bg-purple-500/5 border border-purple-500/20 rounded-xl">
      <div className="flex items-center gap-2 text-xs text-purple-400 mb-2">
        <Bot className="w-4 h-4" />
        <span className="font-semibold">AI Taslağı</span>
        {message.ai_confidence != null && (
          <span className="text-slate-500">· güven: %{Math.round(message.ai_confidence * 100)}</span>
        )}
      </div>
      <div className="text-sm text-slate-200 whitespace-pre-wrap mb-3">{message.ai_draft}</div>
      <div className="flex gap-2">
        <button
          onClick={onApprove}
          disabled={loading}
          className="text-xs bg-green-500/20 hover:bg-green-500/30 text-green-400 border border-green-500/30 px-3 py-1.5 rounded-lg flex items-center gap-1.5"
        >
          <Check className="w-3.5 h-3.5" />
          Onayla & Gönder
        </button>
        <button
          onClick={onReject}
          disabled={loading}
          className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg"
        >
          Düzenle
        </button>
      </div>
    </div>
  )
}
