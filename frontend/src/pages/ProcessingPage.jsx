import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getVideo, getAnalysis } from '../api/videos'

const STEPS = [
  { key: 'audio',    label: 'Extracting audio',        icon: '🎙️' },
  { key: 'visual',   label: 'Analysing body language',  icon: '👁️' },
  { key: 'nlp',      label: 'Analysing language',       icon: '🧠' },
  { key: 'scoring',  label: 'Computing scores',         icon: '📊' },
  { key: 'feedback', label: 'Generating AI feedback',   icon: '✨' },
]

export default function ProcessingPage() {
  const { videoId }         = useParams()
  const navigate            = useNavigate()
  const [status, setStatus] = useState('processing')
  const [step, setStep]     = useState(0)
  const [error, setError]   = useState('')

  useEffect(() => {
    // Animate through steps visually
    const stepTimer = setInterval(() => {
      setStep(prev => (prev < STEPS.length - 1 ? prev + 1 : prev))
    }, 8000)

    // Poll backend every 5 seconds for completion
    const pollTimer = setInterval(async () => {
      try {
        const res = await getVideo(videoId)
        const videoStatus = res.data.status

        if (videoStatus === 'completed') {
          clearInterval(pollTimer)
          clearInterval(stepTimer)
          setStatus('completed')
          setTimeout(() => navigate(`/dashboard/${videoId}`), 1000)
        } else if (videoStatus === 'failed') {
          clearInterval(pollTimer)
          clearInterval(stepTimer)
          setError(res.data.error_message || 'Analysis failed.')
          setStatus('failed')
        }
      } catch (err) {
        console.error('Polling error:', err)
      }
    }, 5000)

    return () => {
      clearInterval(pollTimer)
      clearInterval(stepTimer)
    }
  }, [videoId, navigate])

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">

      {/* Header */}
      <header className="border-b border-gray-800 px-8 py-4 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center text-sm font-bold">S</div>
        <span className="text-lg font-semibold">SpeakWise</span>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-4">
        <div className="w-full max-w-md text-center">

          {status === 'failed' ? (
            <div className="space-y-4">
              <div className="text-5xl">❌</div>
              <h2 className="text-xl font-semibold">Analysis failed</h2>
              <p className="text-red-400 text-sm">{error}</p>
              <button
                onClick={() => navigate('/')}
                className="mt-4 px-6 py-2.5 rounded-xl bg-violet-600 hover:bg-violet-500 text-white font-medium"
              >
                Try again
              </button>
            </div>
          ) : status === 'completed' ? (
            <div className="space-y-4">
              <div className="text-5xl">✅</div>
              <h2 className="text-xl font-semibold">Analysis complete!</h2>
              <p className="text-gray-400">Taking you to your results...</p>
            </div>
          ) : (
            <div className="space-y-8">
              {/* Spinner */}
              <div className="relative w-20 h-20 mx-auto">
                <div className="absolute inset-0 rounded-full border-4 border-gray-800" />
                <div className="absolute inset-0 rounded-full border-4 border-violet-500 border-t-transparent animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center text-2xl">
                  {STEPS[step].icon}
                </div>
              </div>

              <div>
                <h2 className="text-xl font-semibold mb-2">Analysing your speech</h2>
                <p className="text-gray-400 text-sm">This takes 1-3 minutes depending on video length</p>
              </div>

              {/* Steps */}
              <div className="space-y-3 text-left">
                {STEPS.map((s, i) => (
                  <div key={s.key} className="flex items-center gap-3">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs flex-shrink-0 ${
                      i < step  ? 'bg-green-500 text-white' :
                      i === step ? 'bg-violet-600 text-white animate-pulse' :
                      'bg-gray-800 text-gray-600'
                    }`}>
                      {i < step ? '✓' : i + 1}
                    </div>
                    <span className={`text-sm ${
                      i < step   ? 'text-green-400' :
                      i === step ? 'text-white font-medium' :
                      'text-gray-600'
                    }`}>
                      {s.label}
                    </span>
                  </div>
                ))}
              </div>

              <p className="text-xs text-gray-600">
                Video ID: {videoId?.slice(0, 8)}...
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}