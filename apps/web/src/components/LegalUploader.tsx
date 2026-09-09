import { useCallback, useRef, useState } from 'react'
import { UploadCloud, FileText, Image as ImageIcon, FileType2, X, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { api } from '@/lib/api'
import type { LegalDocument } from '@/types'

const ACCEPT = '.pdf,.docx,.txt,.md,.csv,.json,.jpg,.jpeg,.png,.webp,.gif'

export function kindIcon(kind: string) {
  if (kind === 'pdf') return FileType2
  if (kind === 'image') return ImageIcon
  return FileText
}

export function humanSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** Belge yükleyici — dosyayı sunucuya atar, çıkarılan künyeyi üst bileşene verir. */
export function LegalUploader({
  value,
  onChange,
  title = 'Belge yükle',
  hint = 'PDF, Word (.docx), fotoğraf veya düz metin — sürükleyip bırak ya da seç.',
}: {
  value: LegalDocument[]
  onChange: (docs: LegalDocument[]) => void
  title?: string
  hint?: string
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState<string[]>([])

  const upload = useCallback(
    async (files: FileList | File[]) => {
      const list = Array.from(files)
      if (!list.length) return
      setBusy(true)
      setErrors([])
      const added: LegalDocument[] = []
      const failed: string[] = []
      for (const file of list) {
        const form = new FormData()
        form.append('file', file)
        try {
          const { data } = await api.post<LegalDocument>('/legal/documents', form, {
            headers: { 'Content-Type': 'multipart/form-data' },
          })
          added.push(data)
        } catch (err: any) {
          failed.push(`${file.name}: ${err?.response?.data?.detail || 'yüklenemedi'}`)
        }
      }
      if (added.length) onChange([...value, ...added])
      setErrors(failed)
      setBusy(false)
    },
    [onChange, value],
  )

  async function remove(id: number) {
    onChange(value.filter((d) => d.id !== id))
    try {
      await api.delete(`/legal/documents/${id}`)
    } catch {
      /* liste zaten güncellendi, sunucu kaydı kalsa da analizi etkilemez */
    }
  }

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          upload(e.dataTransfer.files)
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') inputRef.current?.click()
        }}
        className={clsx(
          'rounded-2xl border-2 border-dashed px-6 py-8 text-center cursor-pointer transition-colors',
          dragging
            ? 'border-brand-500 bg-brand-500/5'
            : 'border-slate-700 bg-slate-900/40 hover:border-slate-600',
        )}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPT}
          className="hidden"
          onChange={(e) => {
            if (e.target.files) upload(e.target.files)
            e.target.value = ''
          }}
        />
        {busy ? (
          <Loader2 className="w-7 h-7 mx-auto text-brand-400 animate-spin" />
        ) : (
          <UploadCloud className={clsx('w-7 h-7 mx-auto', dragging ? 'text-brand-400' : 'text-slate-500')} />
        )}
        <div className="mt-3 text-sm font-semibold text-slate-200">
          {busy ? 'Yükleniyor ve okunuyor...' : title}
        </div>
        <div className="text-xs text-slate-500 mt-1">{hint}</div>
        <div className="text-[11px] text-slate-600 mt-2">Dosya başına en fazla 12 MB</div>
      </div>

      {errors.length > 0 && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3 space-y-1">
          {errors.map((e) => (
            <p key={e} className="text-sm text-red-300">
              {e}
            </p>
          ))}
        </div>
      )}

      {value.length > 0 && (
        <ul className="space-y-2">
          {value.map((doc) => {
            const Icon = kindIcon(doc.kind)
            return (
              <li
                key={doc.id}
                className="flex items-start gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-3 py-2.5"
              >
                <Icon className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
                <div className="min-w-0 flex-1">
                  <div className="text-sm text-slate-100 truncate">{doc.filename}</div>
                  <div className="text-xs text-slate-500">
                    {humanSize(doc.size)}
                    {doc.pages ? ` · ${doc.pages} sayfa` : ''}
                    {doc.char_count ? ` · ${doc.char_count.toLocaleString('tr-TR')} karakter okundu` : ''}
                    {doc.kind === 'pdf' ? ' · PDF doğrudan okunacak' : ''}
                    {doc.kind === 'image' ? ' · görsel olarak okunacak' : ''}
                  </div>
                  {doc.preview && (
                    <p className="text-xs text-slate-600 mt-1 line-clamp-2">{doc.preview}</p>
                  )}
                  {doc.notes?.map((n) => (
                    <p key={n} className="text-xs text-amber-400/80 mt-1">
                      {n}
                    </p>
                  ))}
                </div>
                <button
                  onClick={() => remove(doc.id)}
                  aria-label={`${doc.filename} kaldır`}
                  className="text-slate-600 hover:text-red-400 transition-colors shrink-0"
                >
                  <X className="w-4 h-4" />
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
