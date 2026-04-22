import { useEffect, useState } from 'react'
import {
  Map,
  Plus,
  Trash2,
  CheckCircle2,
  Circle,
  Clock,
  Flame,
  ChevronDown,
  ChevronRight,
  X,
  Target,
} from 'lucide-react'
import clsx from 'clsx'

type TaskStatus = 'pending' | 'in_progress' | 'done'
type TaskPriority = 'low' | 'medium' | 'high'

interface Task {
  id: string
  title: string
  description?: string
  category: string
  status: TaskStatus
  priority: TaskPriority
  today: boolean
  createdAt: string
  completedAt?: string
}

interface Category {
  slug: string
  name: string
  color: string
  icon: string
}

const CATEGORIES: Category[] = [
  { slug: 'whatsapp', name: 'WhatsApp & AI', color: '#10b981', icon: '💬' },
  { slug: 'dashboard', name: 'Dashboard', color: '#f59e0b', icon: '📊' },
  { slug: 'production', name: 'Production', color: '#3b82f6', icon: '🚀' },
  { slug: 'business', name: 'İş Entegrasyonu', color: '#8b5cf6', icon: '💼' },
  { slug: 'content', name: 'İçerik & SEO', color: '#ec4899', icon: '✍️' },
  { slug: 'personal', name: 'Kişisel', color: '#06b6d4', icon: '☕' },
  { slug: 'other', name: 'Diğer', color: '#64748b', icon: '📝' },
]

// Başlangıç görevleri — dün ve bugün yapılanlar + yapılacaklar
const INITIAL_TASKS: Omit<Task, 'id' | 'createdAt'>[] = [
  // --- DÜN TAMAMLANANLAR ---
  { title: 'Gespa OS v0.1 deploy (Railway)', category: 'production', status: 'done', priority: 'high', today: false, completedAt: '2026-04-20' },
  { title: 'İsim değişikliği: Göksoylar → Gespa OS', category: 'dashboard', status: 'done', priority: 'high', today: false, completedAt: '2026-04-21' },
  { title: 'WhatsApp backend (webhook + AI + inbox)', category: 'whatsapp', status: 'done', priority: 'high', today: false, completedAt: '2026-04-21' },
  { title: 'Meta Developer hesabı + Gespa OS App', category: 'whatsapp', status: 'done', priority: 'high', today: false, completedAt: '2026-04-21' },
  { title: 'WhatsApp test numarası + webhook bağla', category: 'whatsapp', status: 'done', priority: 'high', today: false, completedAt: '2026-04-21' },
  { title: 'AI otomatik cevap sistemi aktif', category: 'whatsapp', status: 'done', priority: 'high', today: false, completedAt: '2026-04-21' },
  { title: 'Viski Saati widget (Dashboard)', category: 'dashboard', status: 'done', priority: 'low', today: false, completedAt: '2026-04-21' },
  { title: 'Yol Haritası sayfası (bu sayfa!)', category: 'dashboard', status: 'done', priority: 'medium', today: true, completedAt: '2026-04-22' },

  // --- BUGÜN (SALI) ---
  { title: 'Permanent WhatsApp token üret (System User)', description: 'Temporary token her 24 saatte expire oluyor. Permanent token süresiz.', category: 'whatsapp', status: 'pending', priority: 'high', today: true },
  { title: 'Hava Durumu widget (Dashboard)', description: 'Manavgat + 5 günlük tahmin, sıcaklık ve yağış', category: 'dashboard', status: 'pending', priority: 'medium', today: true },
  { title: 'Döviz Kuru widget (Dashboard)', description: 'USD, EUR, TRY, GBP — real-time', category: 'dashboard', status: 'pending', priority: 'medium', today: true },
  { title: 'Kahve Saati widget (Dashboard)', description: '10:00 hatırlatma, Viski Saatinin sabah versiyonu', category: 'dashboard', status: 'pending', priority: 'low', today: true },
  { title: 'Sistemi test et (farklı mesaj tipleri)', description: 'Şikayet, fiyat, teklif, acil — AI davranışı kontrol', category: 'whatsapp', status: 'pending', priority: 'medium', today: true },

  // --- BU HAFTA ---
  { title: 'Meta Business Verification başlat', description: 'İşletme bilgilerini doldur, belgeler yükle. 1-10 gün sürer.', category: 'production', status: 'pending', priority: 'high', today: false },
  { title: 'Gespa için iş telefonu hattı (Türk Telekom)', description: 'Yeni bayilik için hat alınacak, production WhatsApp bu numara olacak', category: 'business', status: 'pending', priority: 'high', today: false },
  { title: 'AI ajanlarını aktive et (Satış Uzmanı önce)', description: '12 ajan pasif, tek tek aktive edip test', category: 'whatsapp', status: 'pending', priority: 'medium', today: false },
  { title: 'Lead yönetimi — WhatsApp\'tan otomatik lead', description: 'AI müşteri adayını tanırsa lead olarak kaydetsin', category: 'whatsapp', status: 'pending', priority: 'medium', today: false },

  // --- GELECEK HAFTA+ ---
  { title: 'SEGEM Sigorta Sınavı (16 Mayıs İsparta)', description: 'Hazırlık + sınav günü', category: 'business', status: 'pending', priority: 'high', today: false },
  { title: 'TrafikHızı + PoliçeHızı canlıya', description: 'SEGEM sonrası sigorta platformları aktif', category: 'business', status: 'pending', priority: 'high', today: false },
  { title: 'SSR fix — solaranaliz.tr / internetpaketi.net.tr / tarifesec.net.tr', description: 'Google indexlemiyor, prerender/SSR çözümü lazım', category: 'content', status: 'pending', priority: 'high', today: false },
  { title: 'Email asistanı (Gmail MCP)', description: 'AI mailleri okuyup taslak cevap hazırlasın', category: 'whatsapp', status: 'pending', priority: 'medium', today: false },
  { title: 'Takvim entegrasyonu (Google Calendar)', description: 'Randevu, etkinlik — dashboard\'da bugünkü plan', category: 'dashboard', status: 'pending', priority: 'low', today: false },
  { title: 'Haber ticker (Dashboard)', description: 'Sektörel RSS — solar + telekom + fiber haberleri', category: 'dashboard', status: 'pending', priority: 'low', today: false },
]

const STORAGE_KEY = 'gespa-roadmap-tasks-v1'

function loadTasks(): Task[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) return JSON.parse(saved)
  } catch {}
  // İlk açılış — başlangıç verisini yükle
  return INITIAL_TASKS.map((t, i) => ({
    ...t,
    id: `task_${Date.now()}_${i}`,
    createdAt: t.completedAt || new Date().toISOString(),
  }))
}

function saveTasks(tasks: Task[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks))
  } catch {}
}

export function Roadmap() {
  const [tasks, setTasks] = useState<Task[]>(loadTasks)
  const [newTaskModal, setNewTaskModal] = useState(false)
  const [filter, setFilter] = useState<'all' | 'today' | 'pending' | 'done'>('all')
  const [collapsedCats, setCollapsedCats] = useState<Set<string>>(new Set())

  useEffect(() => {
    saveTasks(tasks)
  }, [tasks])

  const toggleTask = (id: string) => {
    setTasks((prev) =>
      prev.map((t) => {
        if (t.id !== id) return t
        const nextStatus: TaskStatus =
          t.status === 'pending' ? 'in_progress' : t.status === 'in_progress' ? 'done' : 'pending'
        return {
          ...t,
          status: nextStatus,
          completedAt: nextStatus === 'done' ? new Date().toISOString() : undefined,
        }
      }),
    )
  }

  const deleteTask = (id: string) => {
    if (confirm('Bu görevi silmek istediğinize emin misiniz?')) {
      setTasks((prev) => prev.filter((t) => t.id !== id))
    }
  }

  const toggleToday = (id: string) => {
    setTasks((prev) => prev.map((t) => (t.id === id ? { ...t, today: !t.today } : t)))
  }

  const toggleCategory = (slug: string) => {
    setCollapsedCats((prev) => {
      const next = new Set(prev)
      if (next.has(slug)) next.delete(slug)
      else next.add(slug)
      return next
    })
  }

  // Filtrele
  const filtered = tasks.filter((t) => {
    if (filter === 'today') return t.today && t.status !== 'done'
    if (filter === 'pending') return t.status !== 'done'
    if (filter === 'done') return t.status === 'done'
    return true
  })

  // Kategoriye göre grupla
  const grouped: Record<string, Task[]> = {}
  CATEGORIES.forEach((c) => (grouped[c.slug] = []))
  filtered.forEach((t) => {
    if (!grouped[t.category]) grouped[t.category] = []
    grouped[t.category].push(t)
  })

  // İstatistikler
  const total = tasks.length
  const done = tasks.filter((t) => t.status === 'done').length
  const inProgress = tasks.filter((t) => t.status === 'in_progress').length
  const todayCount = tasks.filter((t) => t.today && t.status !== 'done').length
  const pct = total > 0 ? Math.round((done / total) * 100) : 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 flex items-center gap-3">
            <Map className="w-8 h-8 text-brand-400" />
            Yol Haritası
          </h1>
          <p className="text-slate-400 mt-1">Gespa OS'u inşa ederken ilerlemeni takip et.</p>
        </div>
        <button
          onClick={() => setNewTaskModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Yeni Görev
        </button>
      </div>

      {/* Stats + Progress */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <div className="text-sm text-slate-400">Genel İlerleme</div>
          <div className="text-2xl font-bold text-slate-100">
            %{pct}
            <span className="text-sm text-slate-500 ml-2 font-normal">
              {done}/{total}
            </span>
          </div>
        </div>
        <div className="h-2 bg-slate-800 rounded-full overflow-hidden mb-4">
          <div
            className="h-full bg-gradient-to-r from-brand-500 to-green-500 transition-all duration-500"
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="grid grid-cols-4 gap-3 text-center">
          <div>
            <div className="text-2xl font-bold text-green-400">{done}</div>
            <div className="text-xs text-slate-500">Tamamlandı</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-amber-400">{inProgress}</div>
            <div className="text-xs text-slate-500">Devam Ediyor</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-slate-300">{total - done - inProgress}</div>
            <div className="text-xs text-slate-500">Bekliyor</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-red-400">{todayCount}</div>
            <div className="text-xs text-slate-500">Bugün</div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {[
          { k: 'all', label: 'Tümü', count: total },
          { k: 'today', label: 'Bugün', count: todayCount },
          { k: 'pending', label: 'Bekleyen', count: total - done },
          { k: 'done', label: 'Tamamlanan', count: done },
        ].map((f) => (
          <button
            key={f.k}
            onClick={() => setFilter(f.k as any)}
            className={clsx(
              'px-3 py-1.5 rounded-lg text-sm font-medium transition',
              filter === f.k ? 'bg-brand-500 text-slate-950' : 'bg-slate-800 text-slate-400 hover:text-slate-200',
            )}
          >
            {f.label} ({f.count})
          </button>
        ))}
      </div>

      {/* Task Groups */}
      <div className="space-y-4">
        {CATEGORIES.map((cat) => {
          const items = grouped[cat.slug] || []
          if (items.length === 0) return null
          const catDone = items.filter((t) => t.status === 'done').length
          const collapsed = collapsedCats.has(cat.slug)
          return (
            <div key={cat.slug} className="card">
              <button
                onClick={() => toggleCategory(cat.slug)}
                className="w-full flex items-center justify-between mb-3"
              >
                <div className="flex items-center gap-3">
                  {collapsed ? <ChevronRight className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
                  <span className="text-lg">{cat.icon}</span>
                  <h3 className="font-bold text-slate-100">{cat.name}</h3>
                  <span className="text-xs text-slate-500">
                    {catDone}/{items.length}
                  </span>
                </div>
                <div
                  className="h-1 w-24 bg-slate-800 rounded-full overflow-hidden"
                  style={{ marginRight: 8 }}
                >
                  <div
                    className="h-full transition-all"
                    style={{
                      width: `${items.length > 0 ? (catDone / items.length) * 100 : 0}%`,
                      backgroundColor: cat.color,
                    }}
                  />
                </div>
              </button>
              {!collapsed && (
                <div className="space-y-2">
                  {items.map((task) => (
                    <TaskRow
                      key={task.id}
                      task={task}
                      onToggle={() => toggleTask(task.id)}
                      onDelete={() => deleteTask(task.id)}
                      onToggleToday={() => toggleToday(task.id)}
                    />
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* New Task Modal */}
      {newTaskModal && (
        <NewTaskModal
          onClose={() => setNewTaskModal(false)}
          onAdd={(task) => {
            setTasks((prev) => [
              ...prev,
              {
                ...task,
                id: `task_${Date.now()}`,
                createdAt: new Date().toISOString(),
              },
            ])
            setNewTaskModal(false)
          }}
        />
      )}
    </div>
  )
}

function TaskRow({
  task,
  onToggle,
  onDelete,
  onToggleToday,
}: {
  task: Task
  onToggle: () => void
  onDelete: () => void
  onToggleToday: () => void
}) {
  const isDone = task.status === 'done'
  const inProgress = task.status === 'in_progress'
  return (
    <div
      className={clsx(
        'flex items-start gap-3 p-3 rounded-lg border transition',
        isDone
          ? 'bg-green-500/5 border-green-500/20'
          : inProgress
          ? 'bg-amber-500/5 border-amber-500/20'
          : 'bg-slate-800/30 border-slate-800 hover:border-slate-700',
      )}
    >
      <button onClick={onToggle} className="mt-0.5 shrink-0" title="Durumu değiştir">
        {isDone ? (
          <CheckCircle2 className="w-5 h-5 text-green-400" />
        ) : inProgress ? (
          <Clock className="w-5 h-5 text-amber-400" />
        ) : (
          <Circle className="w-5 h-5 text-slate-500" />
        )}
      </button>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <div
            className={clsx(
              'font-medium',
              isDone ? 'text-slate-500 line-through' : 'text-slate-100',
            )}
          >
            {task.title}
          </div>
          {task.today && !isDone && (
            <span className="text-[10px] bg-red-500/20 text-red-400 border border-red-500/30 px-1.5 py-0.5 rounded">
              🔥 BUGÜN
            </span>
          )}
          {task.priority === 'high' && !isDone && (
            <Flame className="w-3 h-3 text-red-400" />
          )}
        </div>
        {task.description && (
          <div className={clsx('text-sm mt-1', isDone ? 'text-slate-600' : 'text-slate-400')}>
            {task.description}
          </div>
        )}
        {isDone && task.completedAt && (
          <div className="text-[10px] text-slate-600 mt-1">
            ✓ Tamamlandı: {new Date(task.completedAt).toLocaleDateString('tr-TR')}
          </div>
        )}
      </div>
      <div className="flex items-center gap-1 shrink-0">
        {!isDone && (
          <button
            onClick={onToggleToday}
            className={clsx(
              'text-xs px-2 py-1 rounded transition',
              task.today
                ? 'bg-red-500/10 text-red-400 border border-red-500/30'
                : 'text-slate-500 hover:text-red-400 hover:bg-red-500/10 border border-slate-700',
            )}
            title="Bugüne ekle/çıkar"
          >
            🔥
          </button>
        )}
        <button
          onClick={onDelete}
          className="text-slate-600 hover:text-red-400 p-1.5 rounded transition"
          title="Sil"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  )
}

function NewTaskModal({
  onClose,
  onAdd,
}: {
  onClose: () => void
  onAdd: (task: Omit<Task, 'id' | 'createdAt'>) => void
}) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('other')
  const [priority, setPriority] = useState<TaskPriority>('medium')
  const [today, setToday] = useState(false)

  const submit = () => {
    if (!title.trim()) return
    onAdd({
      title: title.trim(),
      description: description.trim() || undefined,
      category,
      status: 'pending',
      priority,
      today,
    })
  }

  return (
    <div
      className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Target className="w-5 h-5 text-brand-400" />
            Yeni Görev
          </h2>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="label">Başlık *</label>
            <input
              autoFocus
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && submit()}
              className="input"
              placeholder="Örn: Lead detay sayfası yap"
            />
          </div>
          <div>
            <label className="label">Açıklama (opsiyonel)</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="input min-h-[60px] resize-none"
              placeholder="Detaylar, notlar..."
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Kategori</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="input"
              >
                {CATEGORIES.map((c) => (
                  <option key={c.slug} value={c.slug}>
                    {c.icon} {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Öncelik</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as TaskPriority)}
                className="input"
              >
                <option value="low">Düşük</option>
                <option value="medium">Orta</option>
                <option value="high">Yüksek 🔥</option>
              </select>
            </div>
          </div>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={today}
              onChange={(e) => setToday(e.target.checked)}
              className="w-4 h-4 accent-brand-500"
            />
            <span className="text-sm text-slate-300">🔥 Bugün yapılacaklara ekle</span>
          </label>
        </div>
        <div className="flex gap-2 mt-6">
          <button onClick={onClose} className="btn-secondary flex-1">
            İptal
          </button>
          <button onClick={submit} disabled={!title.trim()} className="btn-primary flex-1">
            Ekle
          </button>
        </div>
      </div>
    </div>
  )
}
