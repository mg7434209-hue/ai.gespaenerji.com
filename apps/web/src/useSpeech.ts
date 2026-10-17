import { useEffect, useRef, useState } from 'react'

type Recognition = { lang: string; interimResults: boolean; continuous: boolean; onresult: ((event: any) => void) | null; onerror: ((event: { error: string }) => void) | null; onend: (() => void) | null; start: () => void; stop: () => void; abort: () => void }

export function useSpeech(onTranscript: (text: string) => void) {
  const [listening, setListening] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [supported, setSupported] = useState(false)
  const [canSpeak, setCanSpeak] = useState(false)
  const recognition = useRef<Recognition | null>(null)
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)
  const startTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const playbackId = useRef(0)
  const callback = useRef(onTranscript)
  callback.current = onTranscript

  useEffect(() => {
    const w = window as Window & { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition }
    setSupported(!!(w.SpeechRecognition || w.webkitSpeechRecognition))
    setCanSpeak('speechSynthesis' in window)
    return () => { if (startTimer.current) clearTimeout(startTimer.current); playbackId.current++; if (recognition.current) { recognition.current.onresult = null; recognition.current.onerror = null; recognition.current.onend = null; recognition.current.abort() }; window.speechSynthesis?.cancel() }
  }, [])

  function stopSpeaking() {
    playbackId.current++
    if (startTimer.current) clearTimeout(startTimer.current)
    startTimer.current = null
    window.speechSynthesis?.cancel()
    utteranceRef.current = null
    setSpeaking(false)
  }
  // Bu çağrı doğrudan dokunma olayında yapılır; mobil ses motorunu hazırlar.
  function prepareAudio() {
    if (!('speechSynthesis' in window)) return
    window.speechSynthesis.resume()
    const primer = new SpeechSynthesisUtterance(' ')
    primer.lang = 'tr-TR'
    primer.volume = 0
    utteranceRef.current = primer
    window.speechSynthesis.speak(primer)
  }
  function speak(text: string) {
    if (!('speechSynthesis' in window)) { setError('Bu tarayıcı sesli okumayı desteklemiyor.'); return }
    stopSpeaking()
    setError(null)
    const token = playbackId.current
    const synth = window.speechSynthesis
    const utterance = new SpeechSynthesisUtterance(text)
    utteranceRef.current = utterance
    utterance.lang = 'tr-TR'
    utterance.volume = 1
    utterance.rate = 1
    const voices = synth.getVoices()
    const voice = voices.find(v => v.lang.toLowerCase().startsWith('tr') && v.localService)
      || voices.find(v => v.lang.toLowerCase().startsWith('tr'))
    if (voice) utterance.voice = voice
    const clearTimer = () => { if (startTimer.current) clearTimeout(startTimer.current); startTimer.current = null }
    utterance.onstart = () => { if (token !== playbackId.current) return; clearTimer(); setSpeaking(true) }
    utterance.onend = () => { if (token !== playbackId.current) return; clearTimer(); utteranceRef.current = null; setSpeaking(false) }
    utterance.onerror = event => {
      if (token !== playbackId.current) return
      clearTimer(); setSpeaking(false); utteranceRef.current = null
      if (event.error !== 'interrupted' && event.error !== 'canceled') setError('Sesli yanıt başlatılamadı. Yanıtı dinle düğmesine dokunun; telefonun medya sesini de kontrol edin.')
    }
    startTimer.current = setTimeout(() => {
      if (token !== playbackId.current) return
      stopSpeaking()
      setError('Tarayıcı otomatik sesli yanıtı başlatmadı. Yanıtı dinle düğmesine dokunun.')
    }, 5000)
    synth.resume()
    synth.speak(utterance)
  }
  function toggleListening() {
    if (listening) { recognition.current?.stop(); return }
    const w = window as Window & { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition }
    const Constructor = w.SpeechRecognition || w.webkitSpeechRecognition
    if (!Constructor) { setError('Mikrofonla yazdırma bu tarayıcıda desteklenmiyor. Klavyenizdeki mikrofonu veya yazılı sohbeti kullanabilirsiniz.'); return }
    stopSpeaking(); prepareAudio(); setError(null)
    const r = new Constructor()
    recognition.current = r
    r.lang = 'tr-TR'; r.interimResults = false; r.continuous = false
    r.onresult = (event) => { const value = event.results[0]?.[0]?.transcript; if (value) callback.current(value) }
    r.onerror = (event) => { setListening(false); if (event.error !== 'aborted') setError(event.error === 'not-allowed' ? 'Mikrofon izni verilmedi. Tarayıcı site ayarlarından izin verin.' : 'Ses alınamadı. Yeniden deneyin veya mesajınızı yazın.') }
    r.onend = () => setListening(false)
    try { r.start(); setListening(true) } catch { setError('Mikrofon başlatılamadı. Yeniden deneyin.') }
  }
  function stopListening() { recognition.current?.abort(); setListening(false) }
  return { listening, speaking, error, supported, canSpeak, speak, prepareAudio, stopSpeaking, toggleListening, stopListening }
}
