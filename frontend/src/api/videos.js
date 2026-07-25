import api from './client'

export const uploadVideo = (file, onProgress) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/videos/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      const pct = Math.round((e.loaded * 100) / e.total)
      onProgress?.(pct)
    },
  })
}

export const getAnalysis = (videoId) => api.get(`/analyses/${videoId}`)
export const getVideo = (videoId) => api.get(`/videos/${videoId}`)