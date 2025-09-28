import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { WebSocketProvider } from './WebSocketContext'
import YappersPage from './pages/YappersPage'
import SettingsPage from './pages/SettingsPage'

export default function App() {
  return (
    <WebSocketProvider>
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/yappers" element={<YappersPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          {/* No default route - accessing root shows nothing */}
        </Routes>
      </Router>
    </WebSocketProvider>
  )
}
