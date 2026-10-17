import { useEffect, useRef, useState } from 'react'

type Recognition = { lang: string; interimResults: boolean; continuous: boolean; onresult: ((event: any) => void) | null; onerror: ((event: { error: string }) => void) | null; onend: (() => void) | null; start: () => void; stop: () => void; abort: () => void }

export function useSpeech(onTranscript: (text: string) => void) {
  const [listening, setListening] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [supported, setSupported] = useState(false)
  const [canSpeak, setCanSpeak] = useState(false)
  const recognition = useRef<Recognition | null>(null)
  const callback = useRef(onTranscript)
  callback.current = onTranscript

  useEffect(() => {
    const w = window as Window & { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition }
    setSupported(!!(w.SpeechRecognition || w.webkitSpeechRecognition))
    setCanSpeak('speechSynthesis' in window)
    return () => { if (recognition.current) { recognition.current.onresult = null; recognition.current.onerror = null; recognition.current.onend = null; recognition.current.abort() }; window.speechSynthesis?.cancel() }
  }, [])

  function stopSpeaking() { window.speechSynthesis?.cancel(); setSpeaking(false) }
  function speak(text: string) {
    if (!('speechSynthesis' in window)) { setError('Bu tarayıcı sesli okumayı desteklemiyor.'); return }
    stopSpeaking()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'tr-TR'
    const voice = window.speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().startsWith('tr'))
    if (voice) utterance.voice = voice
    utterance.onend = () => setSpeaking(false)
    utterance.onerror = () => setSpeaking(false)
    setSpeaking(true)
    window.speechSynthesis.speak(utterance)
  }
  function toggleListening() {
    if (listening) { recognition.current?.stop(); return }
    const w = window as Window & { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition }
    const Constructor = w.SpeechRecognition || w.webkitSpeechRecognition
    if (!Constructor) { setError('Mikrofonla yazdırma bu tarayıcıda desteklenmiyor. Klavyenizdeki mikrofonu veya yazılı sohbeti kullanabilirsiniz.'); return }
    stopSpeaking(); setError(null)
    const r = new Constructor()
    recognition.current = r
    r.lang = 'tr-TR'; r.interimResults = false; r.continuous = false
    r.onresult = (event) => { const value = event.results[0]?.[0]?.transcript; if (value) callback.current(value) }
    r.onerror = (event) => { setListening(false); if (event.error !== 'aborted') setError(event.error === 'not-allowed' ? 'Mikrofon izni verilmedi. Tarayıcı site ayarlarından izin verin.' : 'Ses alınamadı. Yeniden deneyin veya mesajınızı yazın.') }
    r.onend = () => setListening(false)
    try { r.start(); setListening(true) } catch { setError('Mikrofon başlatılamadı. Yeniden deneyin.') }
  }
  function stopListening() { recognition.current?.abort(); setListening(false) }
  return { listening, speaking, error, supported, canSpeak, speak, stopSpeaking, toggleListening, stopListening }
}
