import { useCallback, useEffect, useRef, useState } from 'react'

type Res = ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>
type Rec = {
  lang: string; continuous: boolean; interimResults: boolean; start(): void; stop(): void
  onresult: ((e: { resultIndex: number; results: Res }) => void) | null
  onend: (() => void) | null; onerror: (() => void) | null
}
const Ctor = (): (new () => Rec) | undefined => {
  const w = window as unknown as Record<string, new () => Rec>
  return w.SpeechRecognition ?? w.webkitSpeechRecognition
}

/** Web Speech API wrapper; `supported` is false in browsers without it (hide the mic button). */
export function useSpeech(lang = 'tr-TR', onFinal?: (text: string) => void) {
  const supported = !!Ctor()
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const rec = useRef<Rec | null>(null)
  const cb = useRef(onFinal)
  useEffect(() => { cb.current = onFinal }, [onFinal])

  const start = useCallback(() => {
    const C = Ctor()
    if (!C) return
    const r = new C()
    r.lang = lang
    r.continuous = false
    r.interimResults = true
    r.onresult = (e) => {
      let text = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        text += e.results[i][0].transcript
        if (e.results[i].isFinal) cb.current?.(e.results[i][0].transcript.trim())
      }
      setTranscript(text)
    }
    r.onend = () => setListening(false)
    r.onerror = () => setListening(false)
    rec.current = r
    setTranscript('')
    try { r.start(); setListening(true) } catch { setListening(false) }
  }, [lang])
  const stop = useCallback(() => rec.current?.stop(), [])
  useEffect(() => () => rec.current?.stop(), [])
  return { supported, listening, start, stop, transcript }
}
