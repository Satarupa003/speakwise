import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getAnalysis } from '../api/videos'

/* Small circular score */
const MiniRing = ({ score, label }) => {
  const r = 20, circ = 2 * Math.PI * r
  const fill  = ((score || 0) / 100) * circ
  const color = score >= 80 ? '#22c55e' : score >= 60 ? '#a78bfa' : '#f59e0b'
  return (
    <div className="flex flex-col items-center gap-1">
      <svg width="52" height="52" viewBox="0 0 52 52">
        <circle cx="26" cy="26" r={r} fill="none" stroke="#1f2937" strokeWidth="5"/>
        <circle cx="26" cy="26" r={r} fill="none" stroke={color} strokeWidth="5"
          strokeDasharray={`${fill} ${circ}`} strokeLinecap="round" transform="rotate(-90 26 26)"/>
        <text x="26" y="26" textAnchor="middle" dominantBaseline="central"
          fill="white" fontSize="13" fontWeight="bold">{Math.round(score || 0)}</text>
      </svg>
      <span className="text-[10px] text-gray-500 uppercase tracking-wide">{label}</span>
    </div>
  )
}

const verdictColor = (v = '') => {
  if (v.includes('✅')) return 'text-green-400'
  if (v.includes('⚠️')) return 'text-amber-400'
  if (v.includes('❌')) return 'text-red-400'
  return 'text-gray-400'
}

export default function DashboardPage() {
  const { videoId }             = useParams()
  const navigate                = useNavigate()
  const [a, setA]               = useState(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState('')

  useEffect(() => {
    (async () => {
      try { const res = await getAnalysis(videoId); setA(res.data) }
      catch { setError('Could not load results.') }
      finally { setLoading(false) }
    })()
  }, [videoId])

  if (loading) return (
    <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
      <div className="text-center space-y-3">
        <div className="w-10 h-10 border-4 border-violet-500 border-t-transparent rounded-full animate-spin mx-auto"/>
        <p className="text-gray-400">Loading your coaching report...</p>
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

  const s      = a?.scores || {}
  const fw     = a?.framework || {}
  const fwParts = a?.framework_breakdown || []
  const worked = a?.what_worked_well || []
  const challenges = a?.challenge_questions || []
  const speaking = a?.speaking_specific_feedback || []
  const pts    = a?.improvement_points || []
  const clips  = a?.reference_clips || []

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 px-6 sm:px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center text-sm font-bold">S</div>
          <span className="text-lg font-semibold">SpeakWise</span>
        </div>
        <button onClick={() => navigate('/')}
          className="px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm text-gray-300 transition-colors">
          + New practice
        </button>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8 space-y-6">

        {/* Assessment banner */}
        <div className="bg-gradient-to-br from-violet-900/40 to-gray-900 border border-violet-500/20 rounded-2xl p-6">
          <div className="flex flex-wrap items-center gap-2 mb-3">
            {a?.content_type && (
              <span className="px-3 py-1 rounded-full bg-violet-500/20 text-violet-300 text-xs font-medium capitalize">
                {a.content_type}
              </span>
            )}
            {fw?.name && (
              <span className="px-3 py-1 rounded-full bg-gray-800 text-gray-300 text-xs">
                Framework: {fw.name}
              </span>
            )}
            {a?.overall_score_label && (
              <span className="px-3 py-1 rounded-full bg-green-500/15 text-green-300 text-xs font-medium">
                {a.overall_score_label}
              </span>
            )}
          </div>
          {a?.topic && <p className="text-sm text-gray-500 mb-2">Topic: {a.topic}</p>}
          {a?.feedback_summary && (
            <p className="text-gray-200 text-[15px] leading-relaxed">{a.feedback_summary}</p>
          )}
        </div>

        {/* ⭐ POLISHED BETTER VERSION — leads the page */}
        {a?.polished_version && (
          <div className="bg-gray-900 border-2 border-violet-500/40 rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xl">✨</span>
              <h2 className="text-lg font-bold text-white">How a professional would say it</h2>
            </div>
            <p className="text-xs text-gray-500 mb-4">Your speech rewritten with stronger structure and delivery — same ideas, elevated</p>
            <div className="bg-violet-950/30 rounded-xl p-5 border-l-4 border-violet-500">
              <p className="text-gray-100 text-[15px] leading-relaxed whitespace-pre-line">{a.polished_version}</p>
            </div>
          </div>
        )}

        {/* Framework breakdown */}
        {fwParts.length > 0 && (
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
            <h2 className="text-lg font-semibold mb-1">{fw?.name || 'Framework'} breakdown</h2>
            <p className="text-xs text-gray-500 mb-4">How well each part of the framework came through</p>
            <div className="space-y-3">
              {fwParts.map((part, i) => (
                <div key={i} className="flex gap-3 p-3 bg-gray-800/40 rounded-xl">
                  <div className="flex-shrink-0 w-28">
                    <p className="text-sm font-semibold text-white">{part.part}</p>
                    <p className={`text-xs font-medium ${verdictColor(part.verdict)}`}>{part.verdict}</p>
                  </div>
                  <p className="text-sm text-gray-400 flex-1">{part.observation}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* What worked well */}
        {worked.length > 0 && (
          <div className="bg-green-500/5 border border-green-500/20 rounded-2xl p-6">
            <h2 className="text-lg font-semibold mb-3 text-green-300">✓ What you did well</h2>
            <ul className="space-y-2">
              {worked.map((w, i) => (
                <li key={i} className="flex gap-2 text-sm text-gray-300">
                  <span className="text-green-400 flex-shrink-0">✓</span>{w}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Challenge questions */}
        {challenges.length > 0 && (
          <div className="bg-amber-500/5 border border-amber-500/20 rounded-2xl p-6">
            <h2 className="text-lg font-semibold mb-1 text-amber-300">🤔 Questions you should be ready for</h2>
            <p className="text-xs text-gray-500 mb-3">A sharp interviewer or manager might challenge you with these</p>
            <ul className="space-y-2">
              {challenges.map((q, i) => (
                <li key={i} className="flex gap-2 text-sm text-gray-300">
                  <span className="text-amber-400 flex-shrink-0">Q{i + 1}.</span>{q}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Coaching points */}
        {pts.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-gray-200">Coaching points</h2>
            {pts.map((p, i) => (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded-2xl p-5 space-y-3">
                <span className="px-2.5 py-1 rounded-lg bg-violet-500/20 text-violet-300 text-xs font-medium uppercase tracking-wide">
                  {p.area}
                </span>
                {p.what_happened && (
                  <div><p className="text-xs text-gray-500 uppercase tracking-wide mb-1">What happened</p>
                    <p className="text-sm text-gray-300">{p.what_happened}</p></div>
                )}
                {p.why_it_matters && (
                  <div><p className="text-xs text-gray-500 uppercase tracking-wide mb-1">Why it matters</p>
                    <p className="text-sm text-gray-400 italic">{p.why_it_matters}</p></div>
                )}
                {p.how_to_fix && (
                  <div className="border-l-2 border-violet-500 pl-4">
                    <p className="text-xs text-violet-400 uppercase tracking-wide mb-1">How to fix it</p>
                    <p className="text-sm text-gray-300">{p.how_to_fix}</p></div>
                )}
                {p.practice_exercise && (
                  <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-3">
                    <p className="text-xs text-amber-400 uppercase tracking-wide mb-1">🎯 Practice exercise</p>
                    <p className="text-sm text-gray-300">{p.practice_exercise}</p></div>
                )}
                {p.reference_url && (
                  <div className="bg-red-950/30 border border-red-500/20 rounded-xl p-3">
                    <p className="text-xs text-red-400 uppercase tracking-wide mb-1">📹 Watch this</p>
                    <a href={p.reference_url} target="_blank" rel="noopener noreferrer"
                      className="text-sm font-medium text-white hover:text-violet-300 block">
                      {p.reference_speaker} — {p.reference_title}
                    </a>
                    {p.reference_why && <p className="text-xs text-gray-400 mt-1">{p.reference_why}</p>}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Speaking-specific micro-feedback */}
        {speaking.length > 0 && (
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
            <h2 className="text-lg font-semibold mb-3">Speaking-specific notes</h2>
            <div className="space-y-3">
              {speaking.map((n, i) => (
                <div key={i} className="text-sm space-y-1 border-l-2 border-gray-700 pl-3">
                  <p className="text-gray-300">{n.observation}</p>
                  {n.fix && <p className="text-gray-500">Fix: {n.fix}</p>}
                  {n.example && <p className="text-violet-400 text-xs">{n.example}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* YouTube references */}
        {clips.length > 0 && (
          <div>
            <h2 className="text-lg font-semibold mb-3 text-gray-200">📚 Learn from the best</h2>
            <div className="space-y-2">
              {clips.map((c, i) => (
                <a key={i} href={c.url} target="_blank" rel="noopener noreferrer"
                  className="flex items-start gap-3 p-3 bg-gray-900 border border-gray-800 rounded-xl hover:border-violet-500/40 transition-colors">
                  <div className="w-9 h-9 rounded-lg bg-red-500/20 flex items-center justify-center flex-shrink-0 text-sm">▶</div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{c.speaker} — {c.title}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{c.why}</p>
                  </div>
                </a>
              ))}
            </div>
          </div>
        )}

        {/* Next practice topic */}
        {a?.next_practice_topic && (
          <div className="bg-violet-500/10 border border-violet-500/20 rounded-2xl p-6">
            <h2 className="text-lg font-semibold mb-2 text-violet-300">🎯 Practice this next</h2>
            <p className="text-sm text-gray-300 leading-relaxed">{a.next_practice_topic}</p>
          </div>
        )}

        {/* Scores — small + secondary at the bottom */}
        <div className="bg-gray-900/50 border border-gray-800 rounded-2xl p-5">
          <h2 className="text-sm font-medium text-gray-400 mb-4 uppercase tracking-wide">Score breakdown</h2>
          <div className="flex flex-wrap justify-between gap-3">
            <MiniRing score={s.overall}       label="Overall"/>
            <MiniRing score={s.pace}          label="Pace"/>
            <MiniRing score={s.clarity}       label="Clarity"/>
            <MiniRing score={s.confidence}    label="Confidence"/>
            <MiniRing score={s.engagement}    label="Engage"/>
            <MiniRing score={s.structure}     label="Structure"/>
            <MiniRing score={s.body_language} label="Body"/>
          </div>
        </div>

        {/* Motivational close */}
        {a?.motivational_close && (
          <p className="text-center text-gray-400 text-sm italic px-6">{a.motivational_close}</p>
        )}

        {/* Coach CTA */}
        <div className="bg-violet-900/20 border border-violet-500/20 rounded-2xl p-6 flex flex-col sm:flex-row items-center gap-4">
          <div className="flex-1">
            <h2 className="font-semibold mb-1">Chat with your AI coach</h2>
            <p className="text-gray-400 text-sm">Ask follow-up questions or request more exercises.</p>
          </div>
          <button onClick={() => navigate(`/coach/${videoId}`)}
            className="px-6 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white font-medium text-sm transition-colors whitespace-nowrap">
            Open coach chat →
          </button>
        </div>

      </main>
    </div>
  )
}
