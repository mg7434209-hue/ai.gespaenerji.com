import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  Clock,
  ListChecks,
  BookOpen,
  ShieldAlert,
  FileText,
  Copy,
  Check,
  HelpCircle,
  Wallet,
  ArrowRight,
} from 'lucide-react'
import clsx from 'clsx'
import type { LegalConsultation, LegalReview } from '@/types'
import { LegalActions, LegalChat } from './LegalActions'

// ─────────────────────────────────────────────────────────────
// Danışma sonucu paneli — hem ajan sayfası hem belge analizi kullanır
// ─────────────────────────────────────────────────────────────


export function ResultPanel({
  consultation,
  showActions = true,
  onReview,
}: {
  consultation: LegalConsultation
  showActions?: boolean
  onReview?: (r: LegalReview) => void
}) {
  const r = consultation.result
  if (consultation.status === 'error' || !r) {
    return (
      <div className="card border-red-500/30">
        <div className="flex items-center gap-2 text-red-400 font-semibold mb-2">
          <AlertTriangle className="w-5 h-5" /> Ajan çalıştırılamadı
        </div>
        <p className="text-sm text-slate-400">{consultation.error || 'Bilinmeyen hata.'}</p>
      </div>
    )
  }

  const guvenPct = Math.round((r.guven || 0) * 100)

  return (
    <div className="space-y-4">
      {/* Özet + güven */}
      <div className="card">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              Özet
            </div>
            <p className="text-slate-100 leading-relaxed">{r.ozet}</p>
          </div>
          <div className="text-right shrink-0">
            <div className="text-xs text-slate-500 mb-1">Ajan güveni</div>
            <div
              className={clsx(
                'text-2xl font-bold leading-none',
                guvenPct >= 75 ? 'text-green-400' : guvenPct >= 50 ? 'text-amber-400' : 'text-red-400',
              )}
            >
              %{guvenPct}
            </div>
          </div>
        </div>
        {r.avukat_gerekli && (
          <div className="mt-4 flex gap-2 text-xs text-amber-300/80 bg-amber-500/5 border border-amber-500/20 rounded-lg px-3 py-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            Bu konuda dosyayı bir avukatla birlikte yürütmen önerilir.
          </div>
        )}
      </div>

      {/* Süreler — en kritik blok, en üstte */}
      {r.sureler?.length > 0 && (
        <Section icon={Clock} title="Süreler" accent="text-red-400">
          <div className="space-y-2">
            {r.sureler.map((s, i) => (
              <div
                key={i}
                className={clsx(
                  'rounded-lg border px-3 py-2.5',
                  s.kritik
                    ? 'border-red-500/30 bg-red-500/5'
                    : 'border-slate-800 bg-slate-800/30',
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-slate-100">{s.is}</span>
                  <span
                    className={clsx(
                      'text-xs font-bold px-2 py-0.5 rounded-full',
                      s.kritik ? 'bg-red-500/15 text-red-300' : 'bg-slate-700/50 text-slate-300',
                    )}
                  >
                    {s.sure}
                  </span>
                </div>
                {s.baslangic && (
                  <div className="text-xs text-slate-500 mt-1">Başlangıç: {s.baslangic}</div>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Değerlendirme */}
      {r.degerlendirme && (
        <Section icon={FileText} title="Hukuki değerlendirme">
          <Markdown text={r.degerlendirme} />
        </Section>
      )}

      {/* Adımlar */}
      {r.adimlar?.length > 0 && (
        <Section icon={ListChecks} title="Yapılacaklar">
          <ol className="space-y-3">
            {r.adimlar.map((a, i) => (
              <li key={i} className="flex gap-3">
                <span className="w-6 h-6 rounded-full bg-brand-500/10 text-brand-400 text-xs font-bold flex items-center justify-center shrink-0">
                  {a.sira ?? i + 1}
                </span>
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-slate-100">
                    {a.baslik}
                    {a.kim && (
                      <span className="ml-2 text-[11px] font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                        {a.kim}
                      </span>
                    )}
                  </div>
                  {a.aciklama && (
                    <p className="text-sm text-slate-400 mt-0.5 leading-relaxed">{a.aciklama}</p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </Section>
      )}

      {/* Riskler */}
      {r.riskler?.length > 0 && (
        <Section icon={ShieldAlert} title="Riskler" accent="text-amber-400">
          <div className="space-y-2">
            {r.riskler.map((x, i) => (
              <div key={i} className="rounded-lg border border-slate-800 bg-slate-800/30 px-3 py-2.5">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-slate-100">{x.baslik}</span>
                  {x.seviye && <RiskBadge level={x.seviye} />}
                </div>
                {x.aciklama && <p className="text-sm text-slate-400 mt-1">{x.aciklama}</p>}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Mevzuat */}
      {r.mevzuat?.length > 0 && (
        <Section icon={BookOpen} title="İlgili mevzuat">
          <div className="space-y-2">
            {r.mevzuat.map((m, i) => (
              <div key={i} className="rounded-lg border border-slate-800 bg-slate-800/30 px-3 py-2.5">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-slate-100">{m.kanun}</span>
                  {m.madde && (
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-900 text-brand-400">
                      {m.madde}
                    </span>
                  )}
                  {m.teyit && (
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400">
                      teyit edilmeli
                    </span>
                  )}
                </div>
                {m.aciklama && <p className="text-sm text-slate-400 mt-1">{m.aciklama}</p>}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Eksik bilgiler */}
      {r.eksik_bilgiler?.length > 0 && (
        <Section icon={HelpCircle} title="Ajanın bilmesi gerekenler">
          <ul className="space-y-1.5">
            {r.eksik_bilgiler.map((e, i) => (
              <li key={i} className="text-sm text-slate-300 flex gap-2">
                <span className="text-brand-500/70">?</span>
                <span>{typeof e === 'string' ? e : JSON.stringify(e)}</span>
              </li>
            ))}
          </ul>
          <p className="text-xs text-slate-600 mt-3">
            Bu bilgileri ekleyip tekrar sorarsan cevap belirgin biçimde netleşir.
          </p>
        </Section>
      )}

      {/* Maliyet */}
      {r.maliyet && (
        <Section icon={Wallet} title="Tahmini maliyet">
          <p className="text-sm text-slate-300">{r.maliyet}</p>
        </Section>
      )}

      {/* Belge taslağı */}
      {r.belge?.icerik && <DraftPanel belge={r.belge} />}

      {/* Yönlendirme */}
      {r.sonraki_ajan && (
        <Link
          to={`/hukuk/${r.sonraki_ajan}`}
          className="card flex items-center justify-between hover:border-brand-500/50 transition-colors"
        >
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-wide">Önerilen uzman</div>
            <div className="text-sm text-slate-100 mt-1">
              Bu konunun devamı için <span className="text-brand-400">{r.sonraki_ajan}</span> ajanına geç
            </div>
          </div>
          <ArrowRight className="w-5 h-5 text-brand-400" />
        </Link>
      )}

      {/* Yasal uyarı */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-4 flex gap-3">
        <AlertTriangle className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
        <p className="text-xs text-slate-500 leading-relaxed">{r.uyari}</p>
      </div>

      {/* İndir · denetle · süreleri yaz · konuş */}
      {showActions && (
        <>
          <LegalActions consultation={consultation} onReview={onReview} />
          <LegalChat consultationId={consultation.id} agentName={consultation.agent_name} />
        </>
      )}
    </div>
  )
}

function DraftPanel({ belge }: { belge: { tur?: string; merci?: string; icerik?: string } }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    try {
      await navigator.clipboard.writeText(belge.icerik || '')
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="card">
      <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-blue-400" />
          <div>
            <div className="text-sm font-semibold text-slate-100">
              {belge.tur || 'Belge taslağı'}
            </div>
            {belge.merci && <div className="text-xs text-slate-500">{belge.merci}</div>}
          </div>
        </div>
        <button onClick={copy} className="btn-ghost inline-flex items-center gap-2 text-sm py-2">
          {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
          {copied ? 'Kopyalandı' : 'Metni kopyala'}
        </button>
      </div>
      <pre className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 text-sm text-slate-200 whitespace-pre-wrap font-mono leading-relaxed overflow-x-auto">
        {belge.icerik}
      </pre>
      <p className="text-xs text-slate-600 mt-3">
        Köşeli parantezli alanları doldur, avukatına kontrol ettir; öyle sun.
      </p>
    </div>
  )
}

function RiskBadge({ level }: { level: string }) {
  const map: Record<string, [string, string]> = {
    dusuk: ['Düşük', 'bg-green-500/10 text-green-400'],
    orta: ['Orta', 'bg-amber-500/10 text-amber-400'],
    yuksek: ['Yüksek', 'bg-red-500/10 text-red-400'],
  }
  const [label, cls] = map[level] || [level, 'bg-slate-700/40 text-slate-300']
  return <span className={clsx('text-[11px] font-semibold px-2 py-0.5 rounded-full', cls)}>{label}</span>
}

function Section({
  icon: Icon,
  title,
  accent = 'text-brand-400',
  children,
}: {
  icon: React.ElementType
  title: string
  accent?: string
  children: React.ReactNode
}) {
  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-3">
        <Icon className={clsx('w-4 h-4', accent)} />
        <h3 className="text-sm font-semibold text-slate-200 uppercase tracking-wide">{title}</h3>
      </div>
      {children}
    </div>
  )
}

/** Küçük markdown okuyucu — başlık, liste, kalın metin ve paragraf yeter. */
function Markdown({ text }: { text: string }) {
  const lines = text.split('\n')
  const blocks: React.ReactNode[] = []
  let list: string[] = []

  const flush = (key: string) => {
    if (!list.length) return
    blocks.push(
      <ul key={key} className="space-y-1.5 my-2">
        {list.map((item, i) => (
          <li key={i} className="text-sm text-slate-300 flex gap-2 leading-relaxed">
            <span className="text-brand-500/70 shrink-0">•</span>
            <span>{inline(item)}</span>
          </li>
        ))}
      </ul>,
    )
    list = []
  }

  lines.forEach((raw, i) => {
    const line = raw.trimEnd()
    const bullet = line.match(/^\s*[-*]\s+(.*)$/)
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)$/)
    if (bullet || numbered) {
      list.push((bullet ? bullet[1] : numbered![1]) || '')
      return
    }
    flush(`l${i}`)
    if (!line.trim()) return
    const heading = line.match(/^(#{1,4})\s+(.*)$/)
    if (heading) {
      blocks.push(
        <h4 key={i} className="text-sm font-bold text-slate-100 mt-4 first:mt-0 mb-1">
          {inline(heading[2])}
        </h4>,
      )
      return
    }
    blocks.push(
      <p key={i} className="text-sm text-slate-300 leading-relaxed my-2">
        {inline(line)}
      </p>,
    )
  })
  flush('last')

  return <div>{blocks}</div>
}

/** **kalın** parçalarını ayırır. */
function inline(text: string): React.ReactNode {
  const parts = text.split(/\*\*(.+?)\*\*/g)
  return parts.map((part, i) =>
    i % 2 === 1 ? (
      <strong key={i} className="text-slate-100 font-semibold">
        {part}
      </strong>
    ) : (
      <span key={i}>{part}</span>
    ),
  )
}
