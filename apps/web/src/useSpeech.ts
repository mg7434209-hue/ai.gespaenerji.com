import { useEffect, useRef, useState } from 'react'

type Recognition = { lang: string; interimResults: boolean; continuous: boolean; onresult: ((event: any) => void) | null; onerror: ((event: { error: string }) => void) | null; onend: (() => void) | null; start: () => void; stop: () => void; abort: () => void }

export function useSpeech(onTranscript: (text: string) => void) {
  const [listening, setListening] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [supported, setSupported] = useState(false)
  const [canSpeak, setCanSpeak] = useState(false)
  const recognition = useRef<Recognition | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const streamUrl = useRef<string | null>(null)
  const silenceTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const transcript = useRef('')
  const requestRef = useRef<AbortController | null>(null)
  const playbackId = useRef(0)
  const cached = useRef<{ text: string; url: string } | null>(null)
  const [audioReady, setAudioReady] = useState(false)
  const [preparing, setPreparing] = useState(false)
  const callback = useRef(onTranscript)
  callback.current = onTranscript

  useEffect(() => {
    const w = window as Window & { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition }
    setSupported(!!(w.SpeechRecognition || w.webkitSpeechRecognition))
    setCanSpeak('HTMLAudioElement' in window)
    return () => {
      if (silenceTimer.current) clearTimeout(silenceTimer.current)
      if (streamUrl.current) URL.revokeObjectURL(streamUrl.current)
      playbackId.current++
      requestRef.current?.abort()
      audioRef.current?.pause()
      if (cached.current) URL.revokeObjectURL(cached.current.url)
      if (recognition.current) { recognition.current.onresult = null; recognition.current.onerror = null; recognition.current.onend = null; recognition.current.abort() }
    }
  }, [])

  function stopSpeaking() {
    playbackId.current++
    requestRef.current?.abort()
    requestRef.current = null
    audioRef.current?.pause()
    if (streamUrl.current) { URL.revokeObjectURL(streamUrl.current); streamUrl.current = null }
    setSpeaking(false)
    setPreparing(false)
  }
  function prepareAudio() {
    // Otomatik oynatmayı engelleyen tarayıcılarda kullanıcı yerel oynatıcıya dokunur.
    const audio = audioRef.current
    if (audio) { audio.muted = false; audio.volume = 1 }
  }
  async function speak(text: string) {
    stopSpeaking()
    setError(null)
    const token = playbackId.current
    const input = text.trim().slice(0, 4000)
    if (!input) return
    const audio = audioRef.current
    if (!audio) { setError('Ses oynatıcı açılamadı. Sayfayı yenileyin.'); return }
    prepareAudio()
    setPreparing(true)
    try {
      let url = cached.current?.text === input ? cached.current.url : null
      if (!url) {
        const controller = new AbortController()
        requestRef.current = controller
        const response = await fetch('/api/jarvis/speech', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({text: input}), signal: controller.signal })
        if (!response.ok) {
          const body = await response.json().catch(() => ({}))
          throw new Error(body.detail || 'Ses hazırlanamadı. Yeniden deneyin.')
        }
        const supportsStreaming = 'MediaSource' in window && MediaSource.isTypeSupported('audio/mpeg') && !!response.body
        if (supportsStreaming) {
          const media = new MediaSource()
          const mediaUrl = URL.createObjectURL(media)
          streamUrl.current = mediaUrl
          audio.src = mediaUrl
          const opened = new Promise<void>((resolve, reject) => {
            media.addEventListener('sourceopen', () => resolve(), {once:true})
            controller.signal.addEventListener('abort', () => reject(new DOMException('Canceled', 'AbortError')), {once:true})
          })
          audio.load()
          await opened
          if (token !== playbackId.current) return
          const buffer = media.addSourceBuffer('audio/mpeg')
          const reader = response.body!.getReader()
          const chunks: Uint8Array[] = []
          let started = false
          while (true) {
            const {done, value} = await reader.read()
            if (token !== playbackId.current) { await reader.cancel(); return }
            if (done) break
            chunks.push(value)
            await new Promise<void>((resolve, reject) => {
              const cleanup = () => { buffer.removeEventListener('updateend', updated); buffer.removeEventListener('error', failed); controller.signal.removeEventListener('abort', failed) }
              const updated = () => { cleanup(); resolve() }
              const failed = () => { cleanup(); reject(new Error('Ses akışı kesildi. Yeniden dinlemeyi deneyin.')) }
              buffer.addEventListener('updateend', updated, {once:true})
              buffer.addEventListener('error', failed, {once:true})
              controller.signal.addEventListener('abort', failed, {once:true})
              try { buffer.appendBuffer(value as Uint8Array<ArrayBuffer>) } catch (error) { cleanup(); reject(error) }
            })
            if (!started) {
              started = true
              setAudioReady(true)
              void audio.play().catch(() => { if (token === playbackId.current) { setPreparing(false); setSpeaking(false); setError('Ses hazır. Oynat düğmesine dokunun.') } })
            }
          }
          if (media.readyState === 'open') media.endOfStream()
          if (cached.current) URL.revokeObjectURL(cached.current.url)
          cached.current = {text:input, url:URL.createObjectURL(new Blob(chunks as BlobPart[], {type:'audio/mpeg'}))}
          setPreparing(false)
          return
        }
        const blob = await response.blob()
        if (token !== playbackId.current) return
        if (cached.current) URL.revokeObjectURL(cached.current.url)
        url = URL.createObjectURL(blob)
        cached.current = { text: input, url }
      }
      if (token !== playbackId.current) return
      audio.src = url
      audio.currentTime = 0
      setAudioReady(true)
      setPreparing(false)
      await audio.play()
    } catch (err) {
      if (token !== playbackId.current) return
      setPreparing(false); setSpeaking(false)
      setError(err instanceof DOMException && err.name === 'NotAllowedError'
        ? 'Ses hazır. Aşağıdaki oynat düğmesine dokunun.'
        : err instanceof Error ? err.message : 'Ses oynatılamadı.')
    }
  }
  const onAudioPlay = () => { setPreparing(false); setSpeaking(true); setError(null) }
  const onAudioPause = () => setSpeaking(false)
  const onAudioError = () => { setPreparing(false); setSpeaking(false); setError('Ses dosyası oynatılamadı. Yanıtı dinle ile yeniden deneyin.') }
  function toggleListening() {
    if (listening) { recognition.current?.stop(); return }
    const w = window as Window & { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition }
    const Constructor = w.SpeechRecognition || w.webkitSpeechRecognition
    if (!Constructor) { setError('Mikrofonla yazdırma bu tarayıcıda desteklenmiyor. Klavyenizdeki mikrofonu veya yazılı sohbeti kullanabilirsiniz.'); return }
    stopSpeaking(); prepareAudio(); setError(null)
    const r = new Constructor()
    recognition.current = r
    r.lang = 'tr-TR'; r.interimResults = true; r.continuous = true
    transcript.current = ''
    r.onresult = (event) => {
      transcript.current = Array.from(event.results as ArrayLike<{0: {transcript: string}}>).map(item => item[0]?.transcript || '').join(' ').trim()
      if (silenceTimer.current) clearTimeout(silenceTimer.current)
      silenceTimer.current = setTimeout(() => r.stop(), 1600)
    }
    r.onerror = (event) => { transcript.current = ''; if (silenceTimer.current) clearTimeout(silenceTimer.current); setListening(false); if (event.error !== 'aborted') setError(event.error === 'not-allowed' ? 'Mikrofon izni verilmedi. Tarayıcı site ayarlarından izin verin.' : 'Ses alınamadı. Yeniden deneyin veya mesajınızı yazın.') }
    r.onend = () => { if (silenceTimer.current) clearTimeout(silenceTimer.current); setListening(false); const value = transcript.current; transcript.current = ''; if (value) callback.current(value) }
    try { r.start(); setListening(true) } catch { setError('Mikrofon başlatılamadı. Yeniden deneyin.') }
  }
  function stopListening() { transcript.current = ''; if (silenceTimer.current) clearTimeout(silenceTimer.current); recognition.current?.abort(); setListening(false) }
  return { listening, speaking, error, supported, canSpeak, audioRef, audioReady, preparing, onAudioPlay, onAudioPause, onAudioError, speak, prepareAudio, stopSpeaking, toggleListening, stopListening }
}
