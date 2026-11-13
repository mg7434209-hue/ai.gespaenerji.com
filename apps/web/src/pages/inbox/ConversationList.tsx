import clsx from 'clsx'
import { MessageSquare } from 'lucide-react'
import { MODE_LABEL, displayName, fmtListTime, toUiMode, type Conversation } from './types'

export type Filter = 'all' | 'urgent' | 'unread'

interface Props {
  conversations: Conversation[]      // süzülmüş liste
  counts: { all: number; urgent: number; unread: number }
  filter: Filter
  onFilter: (f: Filter) => void
  selectedId: number | null
  onSelect: (id: number) => void
  status: 'loading' | 'ready' | 'error'
  onRetry: () => void
  searching: boolean
}

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'all', label: 'Tümü' },
  { key: 'urgent', label: 'Acil' },
  { key: 'unread', label: 'Okunmamış' },
]

export function ConversationList({ conversations, counts, filter, onFilter, selectedId, onSelect, status, onRetry, searching }: Props) {
  return (
    <section aria-label="Konuşmalar" className="flex flex-col min-h-0 h-full bg-os-panel border border-os-line rounded-[14px] overflow-hidden">
      <div className="flex gap-2 p-3 border-b border-os-line overflow-x-auto" role="group" aria-label="Konuşma filtresi">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            onClick={() => onFilter(f.key)}
            aria-pressed={filter === f.key}
            className={clsx(
              'min-h-[44px] px-3.5 rounded-[10px] text-[13px] font-semibold whitespace-nowrap transition-colors',
              filter === f.key ? 'bg-os-accent text-os-onaccent' : 'bg-os-bg border border-os-line text-os-text2 hover:bg-os-raised',
            )}
          >
            {f.label} · {counts[f.key]}
          </button>
        ))}
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        {status === 'loading' && <Skeleton />}
        {status === 'error' && (
          <div className="p-6 text-center" role="alert">
            <div className="text-[15px] text-os-text mb-3">Konuşmalar yüklenemedi</div>
            <button type="button" onClick={onRetry} className="min-h-[44px] px-4 rounded-[10px] bg-os-accent text-os-onaccent font-semibold text-sm">
              Tekrar dene
            </button>
          </div>
        )}
        {status === 'ready' && counts.all === 0 && (
          <div className="p-8 text-center text-os-muted">
            <MessageSquare className="w-10 h-10 mx-auto mb-2 opacity-40" aria-hidden="true" />
            <div className="text-[15px] text-os-text2">Henüz konuşma yok</div>
            <div className="text-[13px] mt-1">WhatsApp mesajları geldikçe burada görünür.</div>
          </div>
        )}
        {status === 'ready' && counts.all > 0 && conversations.length === 0 && (
          <div className="p-8 text-center text-[14px] text-os-muted">
            {searching ? 'Aramayla eşleşen konuşma yok.' : 'Bu filtrede konuşma yok.'}
          </div>
        )}
        {status === 'ready' && conversations.length > 0 && (
          <ul>
            {conversations.map((c) => <Row key={c.id} c={c} selected={c.id === selectedId} onSelect={onSelect} />)}
          </ul>
        )}
      </div>
    </section>
  )
}

function Row({ c, selected, onSelect }: { c: Conversation; selected: boolean; onSelect: (id: number) => void }) {
  const name = displayName(c)
  const mode = toUiMode(c.ai_mode)
  return (
    <li>
      <button
        type="button"
        onClick={() => onSelect(c.id)}
        aria-current={selected ? 'true' : undefined}
        className={clsx(
          'w-full text-left flex gap-3 px-3 py-3 min-h-[72px] border-b border-os-line transition-colors',
          selected ? 'bg-os-raised' : 'hover:bg-os-raised/50',
        )}
      >
        <div className="w-10 h-10 shrink-0 rounded-full bg-os-bg border border-os-line2 text-os-accent grid place-items-center font-semibold" aria-hidden="true">
          {name.replace(/^\+/, '').charAt(0).toLocaleUpperCase('tr-TR')}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-2">
            <span className="font-semibold text-[15px] text-os-text truncate">{name}</span>
            <span className="text-xs text-os-muted shrink-0">{fmtListTime(c.last_message_at)}</span>
          </div>
          <div className="text-[13px] text-os-muted truncate mt-0.5">{c.last_message_preview || '—'}</div>
          <div className="flex items-center gap-1.5 mt-1.5">
            <span className="text-xs px-2 py-0.5 rounded-md bg-os-bg border border-os-line text-os-text2">{MODE_LABEL[mode]}</span>
            {c.needs_attention && (
              <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-os-urgentbg text-os-urgentfg">Acil</span>
            )}
            <span className="flex-1" />
            {c.unread_count > 0 && (
              <span className="min-w-[22px] h-[22px] px-1.5 rounded-full bg-os-accent text-os-onaccent text-xs font-bold grid place-items-center" aria-label={`${c.unread_count} okunmamış`}>
                {c.unread_count}
              </span>
            )}
          </div>
        </div>
      </button>
    </li>
  )
}

function Skeleton() {
  return (
    <ul aria-hidden="true" aria-busy="true">
      {Array.from({ length: 6 }).map((_, i) => (
        <li key={i} className="flex gap-3 px-3 py-3 border-b border-os-line animate-pulse">
          <div className="w-10 h-10 rounded-full bg-os-raised" />
          <div className="flex-1 space-y-2 pt-1">
            <div className="h-3.5 w-1/2 rounded bg-os-raised" />
            <div className="h-3 w-4/5 rounded bg-os-raised/70" />
            <div className="h-3 w-1/4 rounded bg-os-raised/50" />
          </div>
        </li>
      ))}
    </ul>
  )
}
