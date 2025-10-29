import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Button } from '../ui/button'
import { Settings, Sun, Moon } from 'lucide-react'
import logger from '../../utils/logger'

function GeneralSettings({ settings, setSettings, updateSettings, apiUrl }) {
  const [tempVolume, setTempVolume] = useState(Math.round((settings.volume !== undefined ? settings.volume : 1.0) * 100))
  const [theme, setTheme] = useState(() => {
    // Get theme from localStorage or default to 'dark'
    return localStorage.getItem('theme') || 'dark'
  })

  useEffect(() => {
    // Apply theme on mount and when it changes
    const root = document.documentElement
    if (theme === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme(prevTheme => prevTheme === 'dark' ? 'light' : 'dark')
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings className="w-5 h-5" />
          General Settings
        </CardTitle>
        <CardDescription>Configure TTS control and audio volume</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Label className="text-base">Theme</Label>
            <p className="text-sm text-muted-foreground">Choose between light and dark mode</p>
          </div>
          <Button
            onClick={toggleTheme}
            variant="outline"
            size="sm"
            className="gap-2"
          >
            {theme === 'dark' ? (
              <>
                <Moon className="w-4 h-4" />
                Dark
              </>
            ) : (
              <>
                <Sun className="w-4 h-4" />
                Light
              </>
            )}
          </Button>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <Label className="text-base">TTS Control</Label>
            <p className="text-sm text-muted-foreground">Stop all TTS and prevent new messages from being spoken</p>
          </div>
          <Button
            onClick={async () => {
              try {
                // Toggle TTS state in backend
                const response = await fetch(`${apiUrl}/api/tts/toggle`, { method: 'POST' })
                const result = await response.json()
                if (result.success) {
                  // Backend is now the source of truth - refetch settings to get accurate state
                  const settingsResponse = await fetch(`${apiUrl}/api/settings`)
                  const settingsData = await settingsResponse.json()
                  setSettings(settingsData)
                  logger.info(`TTS ${result.tts_enabled ? 'enabled' : 'disabled'}`)
                } else {
                  console.error('TTS toggle failed:', result.error)
                }
              } catch (error) {
                console.error('Failed to toggle TTS:', error)
              }
            }}
            variant={settings.ttsControl?.enabled !== false ? "destructive" : "default"}
            size="sm"
          >
            {settings.ttsControl?.enabled !== false ? 'Stop TTS' : 'Resume TTS'}
          </Button>
        </div>

        <div className="space-y-2">
          <Label htmlFor="volume">Audio Volume</Label>
          <div className="flex items-center gap-4">
            <Input
              id="volume"
              type="range"
              min="0"
              max="100"
              step="1"
              value={tempVolume}
              onChange={e => {
                const newVolume = parseInt(e.target.value)
                setTempVolume(newVolume)
                // Update immediately for keyboard input (arrow keys)
                // Mouse drag will be handled by onMouseUp
              }}
              onMouseUp={e => {
                const newVolume = parseInt(e.target.value) / 100
                logger.info(`Volume slider changed to ${Math.round(newVolume * 100)}% (mouse)`)
                updateSettings({ volume: newVolume })
              }}
              onTouchEnd={e => {
                const newVolume = tempVolume / 100
                logger.info(`Volume slider changed to ${Math.round(newVolume * 100)}% (touch)`)
                updateSettings({ volume: newVolume })
              }}
              onKeyUp={e => {
                // Handle keyboard input (arrow keys, page up/down, etc.)
                if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'PageUp', 'PageDown', 'Home', 'End'].includes(e.key)) {
                  const newVolume = tempVolume / 100
                  logger.info(`Volume slider changed to ${Math.round(newVolume * 100)}% (keyboard: ${e.key})`)
                  updateSettings({ volume: newVolume })
                }
              }}
              className="flex-1"
            />
            <span className="text-sm text-muted-foreground w-12 text-right">
              {tempVolume}%
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default GeneralSettings