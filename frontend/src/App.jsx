import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import UploadPage     from './pages/UploadPage'
import ProcessingPage from './pages/ProcessingPage'
import DashboardPage  from './pages/DashboardPage'
import CoachPage      from './pages/CoachPage'
import ProgressPage   from './pages/ProgressPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"                      element={<UploadPage />} />
        <Route path="/processing/:videoId"   element={<ProcessingPage />} />
        <Route path="/dashboard/:videoId"    element={<DashboardPage />} />
        <Route path="/coach/:videoId"        element={<CoachPage />} />
        <Route path="/progress"              element={<ProgressPage />} />
        <Route path="*"                      element={<Navigate to="/" />} />
      </Routes>
    </BrowserRouter>
  )
}