import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getAnalysis, coachChat } from '../api/videos'
import api from '../api/client'

const DEFAULT_SUGGESTIONS = [
  'Why did I appear nervous?',
  'Give me a confidence drill',
  'Rewrite my answer using STAR',
  'Simulate a tough interview question',
]

export default function CoachPage() {
  const { videoId }            = useParams()
  const navigate               = useNavigate()
  const bottomRef              = useRef(null)
  const inputRef               = useRef(null)

  const [analysis, setAnalysis]     = useState(null)
  const [messages, setMessages]     = useState([])   // [{role, text}]
  const [input, setInput]           = useState('')
  const [sending, setSending]       = useState(false)
  const [suggestions, setSuggestions] = useState(DEFAULT_SUGGESTIONS)
  const [error, setError]           = useState('')

  // Load analysis for the context banner
  useEffect(() => {
    getAnalysis(videoId)
      .then(r => setAnalysis(r.data))
      .catch(() => {})  // optional — coach still works without it
  }, [videoId])

  // Auto-scroll to newest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  const send = async (text) => {
    const trimmed = text.trim()
    if (!trimmed || sending) return
    setInput('')
    setError('')
    setSending(true)
    setMessages(prev => [...prev, { role: 'user', text: trimmed }])

    try {
      const res = await coachChat(videoId, trimmed)
      const { reply, suggestions: sugg } = res.data
      setMessages(prev => [...prev, { role: 'coach', text: reply }])
      if (sugg && sugg.length) setSuggestions(sugg)
    } catch (e) {
      const msg = e.response?.data?.detail || 'Could not reach coach — is Ollama running?'
      setError(msg)
      setMessages(prev => [...prev, { role: 'error', text: msg }])
    } finally {
      setSending(false)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }

  const handleReset = async () => {
    try { await api.post(`/coach/reset/${videoId}`) } catch (_) {}
    setMessages([])
    setSuggestions(DEFAULT_SUGGESTIONS)
    setError('')
  }

  const s = analysis?.scores || {}
  const scoreItems = [
    { label: 'Overall',    val: s.overall },
    { label: 'Confidence', val: s.confidence },
    { label: 'Delivery',   val: s.delivery },
    { label: 'Clarity',    val: s.clarity },
    { label: 'Structure',  val: s.structure },
  ].filter(x => x.val != null)

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">

      {/* ── Header ── */}
      <header className="border-b border-gray-800 px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(`/dashboard/${videoId}`)}
            className="text-gray-500 hover:text-gray-300 text-sm transition-colors"
          >
            ← Back
          </button>
          <div className="w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center text-sm font-bold">S</div>
          <span className="text-base font-semibold">SpeakWise Coach</span>
        </div>
        <button
          onClick={handleReset}
          className="text-xs text-gray-500 hover:text-gray-300 border border-gray-700 hover:border-gray-500 px-3 py-1.5 rounded-lg transition-colors"
        >
          Reset chat
        </button>
      </header>

      {/* ── Analysis context banner ── */}
      {scoreItems.length > 0 && (
        <div className="border-b border-gray-800/60 bg-gray-900/40 px-6 py-3 flex flex-wrap gap-4 flex-shrink-0">
          {scoreItems.map(({ label, val }) => (
            <div key={label} className="flex items-center gap-1.5">
              <span className="text-xs text-gray-500">{label}</span>
              <span className={`text-sm font-semibold ${
                val >= 80 ? 'text-green-400' : val >= 60 ? 'text-violet-400' : 'text-amber-400'
              }`}>{Math.round(val)}</span>
            </div>
          ))}
          {analysis?.scenario && (
            <span className="text-xs text-gray-600 capitalize ml-auto self-center">
              {analysis.scenario}{analysis.topic ? ` · ${analysis.topic}` : ''}
            </span>
          )}
        </div>
      )}

      {/* ── Chat area ── */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 max-w-3xl w-full mx-auto">

        {/* Welcome message if no history */}
        {messages.length === 0 && (
          <div className="text-center space-y-3 pt-8">
            <div className="w-14 h-14 rounded-2xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-2xl mx-auto">
              🎤
            </div>
            <p className="text-gray-300 font-medium">Hi! I'm your SpeakWise Coach.</p>
            <p className="text-gray-500 text-sm max-w-sm mx-auto">
              I've reviewed your analysis. Ask me anything — I can explain your scores,
              give you drills, rewrite your answer, or simulate a tough interviewer.
            </p>
          </div>
        )}

        {/* Message bubbles */}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {m.role !== 'user' && (
              <div className="w-7 h-7 rounded-lg bg-violet-600/30 border border-violet-500/30 flex items-center justify-center text-sm flex-shrink-0 mt-0.5 mr-2">
                S
              </div>
            )}
            <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
              m.role === 'user'
                ? 'bg-violet-600 text-white rounded-br-sm'
                : m.role === 'error'
                ? 'bg-red-900/40 border border-red-500/30 text-red-300'
                : 'bg-gray-800/80 border border-gray-700/50 text-gray-100 rounded-bl-sm'
            }`}>
              {m.text}
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {sending && (
          <div className="flex justify-start">
            <div className="w-7 h-7 rounded-lg bg-violet-600/30 border border-violet-500/30 flex items-center justify-center text-sm flex-shrink-0 mt-0.5 mr-2">S</div>
            <div className="bg-gray-800/80 border border-gray-700/50 rounded-2xl rounded-bl-sm px-4 py-3">
              <span className="flex gap-1 items-center">
                <span className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Suggestions ── */}
      <div className="px-4 pb-2 max-w-3xl w-full mx-auto">
        <div className="flex flex-wrap gap-2">
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => send(s)}
              disabled={sending}
              className="text-xs px-3 py-1.5 rounded-lg border border-gray-700 text-gray-400 hover:border-violet-500/60 hover:text-violet-300 hover:bg-violet-500/5 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* ── Input bar ── */}
      <div className="border-t border-gray-800 px-4 py-4 max-w-3xl w-full mx-auto flex-shrink-0">
        <form
          onSubmit={(e) => { e.preventDefault(); send(input) }}
          className="flex gap-3 items-end"
        >
          <textarea
            ref={inputRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input) }
            }}
            placeholder="Ask your coach anything..."
            disabled={sending}
            className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500 transition-colors resize-none disabled:opacity-50"
            style={{ minHeight: '48px', maxHeight: '140px' }}
          />
          <button
            type="submit"
            disabled={!input.trim() || sending}
            className="w-11 h-11 rounded-xl bg-violet-600 hover:bg-violet-500 flex items-center justify-center text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
          >
            {sending
              ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              : <span className="text-lg">↑</span>
            }
          </button>
        </form>
        <p className="text-xs text-gray-700 mt-2 text-center">
          Shift+Enter for new line · Enter to send · Powered by Ollama llama3.2 (local)
        </p>
      </div>

    </div>
  )
}
