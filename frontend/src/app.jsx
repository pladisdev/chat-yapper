import React, { useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { WebSocketProvider } from './WebSocketContext'
import YappersPage from './pages/YappersPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  useEffect(() => {
    // Apply saved theme preference or default to dark mode
    const savedTheme = localStorage.getItem('theme') || 'dark'
    if (savedTheme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [])

  return (
    <WebSocketProvider>
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/" element={<Navigate to="/settings" replace />} />
          <Route path="/yappers" element={<YappersPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </Router>
    </WebSocketProvider>
  )
}
