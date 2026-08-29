import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getProgress } from '../api/videos'

/* Small sparkline-style trend row for one metric across all sessions */
const TrendRow = ({ label, values, lowerIsBetter = false, unit = '' }) => {
  const pts = values.filter(v => v != null)
  if (pts.length === 0) return null
  const max = Math.max(...pts), min = Math.min(...pts)
  const first = pts[0], last = pts[pts.length - 1]
  const delta = last - first
  const improved = lowerIsBetter ? delta < 0 : delta > 0
  const flat = Math.abs(delta) < 2
  const color = flat ? 'text-gray-400' : improved ? 'text-green-400' : 'text-amber-400'
  const arrow = flat ? '→' : improved ? '↑' : '↓'

  return (
    <div className="flex items-center gap-4 py-3 border-b border-gray-800/60 last:border-0">
      <span className="text-sm text-gray-300 w-40 flex-shrink-0">{label}</span>
      <div className="flex-1 flex items-end gap-1 h-8">
        {values.map((v, i) => {
          const h = v == null ? 0 : max === min ? 50 : ((v - min) / (max - min)) * 24 + 4
          return (
            <div key={i} title={v == null ? 'n/a' : `${v}${unit}`}
              className={`flex-1 rounded-sm ${v == null ? 'bg-gray-800' : 'bg-violet-500/60'}`}
              style={{ height: `${h}px` }} />
          )
        })}
      </div>
      <span className={`text-sm font-semibold w-16 text-right flex-shrink-0 ${color}`}>
        {arrow} {Math.round(Math.abs(delta))}{unit}
      </span>
    </div>
  )
}

export default function ProgressPage() {
  const navigate = useNavigate()
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')

  useEffect(() => {
    (async () => {
      try { const res = await getProgress(); setData(res.data) }
      catch { setError('Could not load your progress history.') }
      finally { setLoading(false) }
    })()
  }, [])

  if (loading) return (
    <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
      <div className="text-center space-y-3">
        <div className="w-10 h-10 border-4 border-violet-500 border-t-transparent rounded-full animate-spin mx-auto" />
        <p className="text-gray-400">Loading your progress...</p>
      </div>
    </div>
  )

  if (error) return (
    <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
      <div className="text-center space-y-3">
        <p className="text-red-400">{error}</p>
        <button onClick={() => navigate('/')} className="px-4 py-2 bg-violet-600 rounded-lg text-sm">Go back</button>
      </div>
    </div>
  )

  const entries = data?.entries || []

  if (entries.length === 0) return (
    <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
      <div className="text-center space-y-3 max-w-sm px-4">
        <div className="w-14 h-14 rounded-2xl bg-violet-600/20 border border-violet-500/30 flex items-center justify-center text-2xl mx-auto">📈</div>
        <p className="text-gray-300 font-medium">No sessions recorded yet.</p>
        <p className="text-gray-500 text-sm">Analyze a video to start tracking your progress over time.</p>
        <button onClick={() => navigate('/')} className="px-4 py-2 bg-violet-600 hover:bg-violet-500 rounded-lg text-sm transition-colors">
          Upload a video
        </button>
      </div>
    </div>
  )

  const metrics = [
    { label: 'Overall',            key: 'overall',            lowerIsBetter: false },
    { label: 'Confidence',         key: 'confidence',         lowerIsBetter: false },
    { label: 'Body language',      key: 'body_language',      lowerIsBetter: false },
    { label: 'Emotional presence', key: 'emotional_presence', lowerIsBetter: false },
    { label: 'Eye contact',        key: 'eye_contact',        lowerIsBetter: false, unit: '%' },
    { label: 'Filler word rate',   key: 'filler_word_rate',   lowerIsBetter: true,  unit: '/min' },
  ]

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-6 sm:px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center text-sm font-bold">S</div>
          <span className="text-lg font-semibold">SpeakWise</span>
        </div>
        <button onClick={() => navigate('/')}
          className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm text-gray-300 transition-colors">
          ← New session
        </button>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-8 py-8 space-y-8">

        {/* Summary */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-5 space-y-2">
          <h1 className="text-lg font-semibold">Your Progress</h1>
          <p className="text-sm text-gray-400">{data.summary || `${data.total_sessions} session(s) recorded.`}</p>
          <div className="flex flex-wrap gap-2 pt-1">
            {(data.improving || []).map(m => (
              <span key={m} className="text-xs px-2.5 py-1 rounded-full bg-green-500/10 border border-green-500/30 text-green-400">
                ↑ {m}
              </span>
            ))}
            {(data.regressing || []).map(m => (
              <span key={m} className="text-xs px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400">
                ↓ {m}
              </span>
            ))}
          </div>
        </div>

        {/* Trends across sessions */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-2">Trends across {entries.length} session(s)</h2>
          {metrics.map(m => (
            <TrendRow
              key={m.key}
              label={m.label}
              values={entries.map(e => e[m.key])}
              lowerIsBetter={m.lowerIsBetter}
              unit={m.unit || ''}
            />
          ))}
        </div>

        {/* Session history */}
        <div className="bg-gray-900/60 border border-gray-800 rounded-2xl p-5">
          <h2 className="text-sm font-semibold text-gray-300 mb-3">Session history</h2>
          <div className="space-y-2">
            {[...entries].reverse().map((e, i) => {
              const failed = e.status === 'failed'
              return (
                <button
                  key={e.video_id + i}
                  onClick={() => navigate(`/dashboard/${e.video_id}`)}
                  className={`w-full flex items-center justify-between gap-3 px-3 py-2.5 rounded-xl border text-left transition-colors ${
                    failed
                      ? 'border-red-500/20 bg-red-950/10 hover:border-red-500/40'
                      : 'border-gray-800 hover:border-violet-500/50 hover:bg-violet-500/5'
                  }`}
                >
                  <div className="min-w-0">
                    <p className="text-sm text-gray-200 truncate">
                      {e.scenario || 'Session'}{e.topic ? ` · ${e.topic}` : ''}
                    </p>
                    <p className="text-xs text-gray-500">{e.date || 'unknown date'}</p>
                  </div>
                  {failed ? (
                    <span className="text-xs px-2.5 py-1 rounded-full bg-red-500/10 border border-red-500/30 text-red-400 flex-shrink-0">
                      ❌ Generation failed
                    </span>
                  ) : (
                    <span className={`text-sm font-semibold flex-shrink-0 ${
                      e.overall >= 80 ? 'text-green-400' : e.overall >= 60 ? 'text-violet-400' : 'text-amber-400'
                    }`}>
                      {e.overall != null ? Math.round(e.overall) : '—'}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>

      </main>
    </div>
  )
}
