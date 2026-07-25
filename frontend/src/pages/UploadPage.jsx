import { useState, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'

const ACCEPTED_TYPES = ['video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo']
const MAX_SIZE_MB    = 500

const CONTENT_TYPES = [
  { id: 'interview',       label: 'Job Interview',       icon: '💼', desc: 'Practice STAR/PREP answers' },
  { id: 'presentation',    label: 'Presentation',        icon: '📊', desc: 'Slides, demos, pitches' },
  { id: 'discussion',      label: 'Group Discussion',    icon: '🗣️', desc: 'GD, debate, panel' },
  { id: 'corporate',       label: 'Corporate Speech',    icon: '🏢', desc: 'Town halls, team updates' },
  { id: 'speech',          label: 'Public Speech',       icon: '🎤', desc: 'TEDx, keynote, ceremony' },
  { id: 'pitch',           label: 'Startup Pitch',       icon: '🚀', desc: 'Investors, demo day' },
  { id: 'social',          label: 'Social / Casual',     icon: '☕', desc: 'Networking, small talk' },
  { id: 'humor',           label: 'Humor / Comedy',      icon: '😄', desc: 'Stand-up, roast, MC' },
  { id: 'formal',          label: 'Formal Address',      icon: '🎓', desc: 'Graduation, awards' },
  { id: 'leadership',      label: 'Leadership Comm.',    icon: '⭐', desc: 'Motivating teams, vision' },
]

export default function UploadPage() {
  const [isDragging, setIsDragging]     = useState(false)
  const [file, setFile]                 = useState(null)
  const [contentType, setContentType]   = useState(null)
  const [topic, setTopic]               = useState('')
  const [progress, setProgress]         = useState(0)
  const [uploading, setUploading]       = useState(false)
  const [error, setError]               = useState('')
  const fileInputRef                    = useRef(null)
  const navigate                        = useNavigate()

  const validate = (f) => {
    if (!ACCEPTED_TYPES.includes(f.type))
      return 'Please upload MP4, WebM, MOV, or AVI.'
    if (f.size > MAX_SIZE_MB * 1024 * 1024)
      return `File too large. Max ${MAX_SIZE_MB}MB.`
    return null
  }

  const handleFile = (f) => {
    const err = validate(f)
    if (err) { setError(err); return }
    setError('')
    setFile(f)
  }

  const onDrop = useCallback((e) => {
    e.preventDefault(); setIsDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }, [])

  const canUpload = file && contentType

  const handleUpload = async () => {
    if (!canUpload) return
    setUploading(true); setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)
      // Pass content type and topic as query params
      const params = new URLSearchParams({ content_type: contentType })
      if (topic.trim()) params.append('topic', topic.trim())

      const res = await api.post(`/videos/upload?${params}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => setProgress(Math.round((e.loaded * 100) / e.total)),
      })
      navigate(`/processing/${res.data.id}`)
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed. Is the backend running?')
      setUploading(false)
    }
  }

  const formatSize = (bytes) => (bytes / (1024 * 1024)).toFixed(1) + ' MB'

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">

      {/* Header */}
      <header className="border-b border-gray-800 px-8 py-4 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center text-sm font-bold">S</div>
        <span className="text-lg font-semibold">SpeakWise</span>
        <span className="text-gray-600 text-sm ml-1">— AI Communication Mentor</span>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        <div className="w-full max-w-2xl space-y-8">

          {/* Title */}
          <div className="text-center">
            <h1 className="text-3xl font-bold mb-2">Practice your speaking</h1>
            <p className="text-gray-400">Upload a video and get mentor-quality coaching with a polished rewrite</p>
          </div>

          {/* Step 1 — Content type */}
          <div>
            <p className="text-sm font-medium text-gray-300 mb-3">
              <span className="text-violet-400 font-bold">Step 1</span> — What type of speaking is this?
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {CONTENT_TYPES.map((ct) => (
                <button key={ct.id} onClick={() => setContentType(ct.id)}
                  className={`flex items-start gap-3 p-3 rounded-xl border text-left transition-all ${
                    contentType === ct.id
                      ? 'border-violet-500 bg-violet-500/15'
                      : 'border-gray-800 bg-gray-900 hover:border-gray-600'
                  }`}>
                  <span className="text-xl flex-shrink-0">{ct.icon}</span>
                  <div>
                    <p className={`text-sm font-medium ${contentType === ct.id ? 'text-violet-300' : 'text-white'}`}>
                      {ct.label}
                    </p>
                    <p className="text-xs text-gray-500 mt-0.5">{ct.desc}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Step 2 — Topic (optional) */}
          <div>
            <p className="text-sm font-medium text-gray-300 mb-2">
              <span className="text-violet-400 font-bold">Step 2</span> — What topic did you speak on?
              <span className="text-gray-600 ml-1">(optional but helps AI give better feedback)</span>
            </p>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder='e.g. "Should freshers switch jobs?" or "Q3 sales review"'
              className="w-full bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-violet-500 transition-colors"
            />
          </div>

          {/* Step 3 — Upload */}
          <div>
            <p className="text-sm font-medium text-gray-300 mb-3">
              <span className="text-violet-400 font-bold">Step 3</span> — Upload your video
            </p>

            <div
              onDrop={onDrop}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
              onDragLeave={() => setIsDragging(false)}
              onClick={() => !file && fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-2xl p-10 text-center transition-all cursor-pointer ${
                isDragging  ? 'border-violet-500 bg-violet-500/10' :
                file        ? 'border-green-500 bg-green-500/5 cursor-default' :
                              'border-gray-700 hover:border-gray-500 hover:bg-gray-900/50'
              }`}
            >
              <input ref={fileInputRef} type="file" accept="video/*" className="hidden"
                onChange={(e) => e.target.files[0] && handleFile(e.target.files[0])}/>

              {file ? (
                <div className="space-y-2">
                  <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center mx-auto text-xl">✓</div>
                  <p className="font-medium">{file.name}</p>
                  <p className="text-sm text-gray-400">{formatSize(file.size)}</p>
                  <button onClick={(e) => { e.stopPropagation(); setFile(null) }}
                    className="text-xs text-gray-500 hover:text-gray-300 underline">
                    Choose different file
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="text-4xl">📹</div>
                  <p className="text-base font-medium">
                    {isDragging ? 'Drop your video here' : 'Drag and drop your video'}
                  </p>
                  <p className="text-sm text-gray-500">or <span className="text-violet-400">browse files</span></p>
                  <p className="text-xs text-gray-600">MP4, WebM, MOV or AVI · Max {MAX_SIZE_MB}MB</p>
                </div>
              )}
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">{error}</div>
          )}

          {/* Upload button */}
          {!uploading && (
            <button onClick={handleUpload} disabled={!canUpload}
              className={`w-full py-4 rounded-xl text-white font-semibold text-base transition-all ${
                canUpload
                  ? 'bg-violet-600 hover:bg-violet-500 cursor-pointer'
                  : 'bg-gray-800 text-gray-600 cursor-not-allowed'
              }`}>
              {!contentType ? 'Select a content type to continue' :
               !file        ? 'Upload a video to continue' :
                              `Analyse my ${CONTENT_TYPES.find(c=>c.id===contentType)?.label} →`}
            </button>
          )}

          {/* Progress */}
          {uploading && (
            <div className="space-y-3">
              <div className="flex justify-between text-sm text-gray-400">
                <span>Uploading...</span><span>{progress}%</span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-2">
                <div className="bg-violet-600 h-2 rounded-full transition-all" style={{ width: `${progress}%` }}/>
              </div>
              <p className="text-xs text-gray-500 text-center">Analysis starts automatically after upload</p>
            </div>
          )}

          {/* Tips */}
          <div className="grid grid-cols-3 gap-3 pt-2">
            {[
              { icon: '💡', title: 'Good lighting', desc: 'Face a window or lamp' },
              { icon: '🎤', title: 'Clear audio',   desc: 'Quiet room, mic nearby' },
              { icon: '📸', title: 'Full frame',    desc: 'Head and shoulders visible' },
            ].map(tip => (
              <div key={tip.title} className="bg-gray-900 rounded-xl p-3 text-center">
                <div className="text-xl mb-1">{tip.icon}</div>
                <p className="text-xs font-medium text-gray-300">{tip.title}</p>
                <p className="text-xs text-gray-600 mt-0.5">{tip.desc}</p>
              </div>
            ))}
          </div>

        </div>
      </main>
    </div>
  )
}
