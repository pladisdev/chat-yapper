import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Button } from '../ui/button'
import { Settings } from 'lucide-react'
import logger from '../../utils/logger'

function GeneralSettings({ settings, updateSettings, apiUrl }) {
  const [tempVolume, setTempVolume] = useState(Math.round((settings.volume !== undefined ? settings.volume : 1.0) * 100))

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings className="w-5 h-5" />
          General Settings
        </CardTitle>
        <CardDescription>Configure avatar display and layout</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Label className="text-base">TTS Control</Label>
            <p className="text-sm text-muted-foreground">Stop all TTS and prevent new messages from being spoken</p>
          </div>
          <Button
            onClick={async () => {
              try {
                const currentState = settings.ttsControl?.enabled !== false
                const response = await fetch(`${apiUrl}/api/tts/toggle`, { method: 'POST' })
                const result = await response.json()
                if (result.success) {
                  // Update settings to reflect new state
                  updateSettings({ ttsControl: { enabled: result.tts_enabled } })
                  logger.info(`✅ TTS ${result.tts_enabled ? 'enabled' : 'disabled'}`)
                } else {
                  console.error('❌ TTS toggle failed:', result.error)
                }
              } catch (error) {
                console.error('❌ Failed to toggle TTS:', error)
              }
            }}
            variant={settings.ttsControl?.enabled !== false ? "destructive" : "default"}
            size="sm"
          >
            {settings.ttsControl?.enabled !== false ? '🔇 Stop TTS' : '🔊 Resume TTS'}
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
              onChange={e => setTempVolume(parseInt(e.target.value))}
              onMouseUp={e => updateSettings({ volume: parseInt(e.target.value) / 100 })}
              onTouchEnd={e => updateSettings({ volume: tempVolume / 100 })}
              className="flex-1"
            />
            <span className="text-sm text-muted-foreground w-12 text-right">
              {tempVolume}%
            </span>
          </div>
        </div>

        <div className="pt-4 border-t space-y-6">
          <div className="space-y-2">
            <Label htmlFor="avatarRows">Number of Avatar Rows</Label>
            <Input
              id="avatarRows"
              type="number"
              min="1"
              max="10"
              value={settings.avatarRows || 2}
              onChange={e => {
                const newRows = parseInt(e.target.value) || 2
                const currentRowConfig = settings.avatarRowConfig || [6, 6]
                let newRowConfig = [...currentRowConfig]
                if (newRows > currentRowConfig.length) {
                  while (newRowConfig.length < newRows) {
                    newRowConfig.push(6)
                  }
                } else if (newRows < currentRowConfig.length) {
                  newRowConfig = newRowConfig.slice(0, newRows)
                }
                updateSettings({ avatarRows: newRows, avatarRowConfig: newRowConfig })
              }}
            />
          </div>

          <div className="space-y-3">
            <Label>Avatars Per Row Configuration</Label>
            <div className="space-y-2">
              {(settings.avatarRowConfig || [6, 6]).slice(0, settings.avatarRows || 2).map((avatarsInRow, rowIndex) => (
                <div key={rowIndex} className="flex items-center gap-3">
                  <Label className="w-16 text-muted-foreground">Row {rowIndex + 1}:</Label>
                  <Input
                    type="number"
                    min="1"
                    max="20"
                    value={avatarsInRow}
                    onChange={e => {
                      const newConfig = [...(settings.avatarRowConfig || [6, 6])]
                      newConfig[rowIndex] = parseInt(e.target.value) || 1
                      updateSettings({ avatarRowConfig: newConfig })
                    }}
                  />
                </div>
              ))}
            </div>
            <p className="text-sm text-muted-foreground">
              Total avatars: {(settings.avatarRowConfig || [6, 6]).slice(0, settings.avatarRows || 2).reduce((sum, count) => sum + count, 0)}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="avatarSize">Avatar Size (px)</Label>
            <Input
              id="avatarSize"
              type="number"
              min="20"
              max="200"
              value={settings.avatarSize || 60}
              onChange={e => updateSettings({ avatarSize: parseInt(e.target.value) || 60 })}
            />
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="avatarSpacingX">Horizontal Spacing (px)</Label>
              <Input
                id="avatarSpacingX"
                type="number"
                min="10"
                max="200"
                value={settings.avatarSpacingX || settings.avatarSpacing || 50}
                onChange={e => updateSettings({ avatarSpacingX: parseInt(e.target.value) || 50 })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="avatarSpacingY">Vertical Spacing (px)</Label>
              <Input
                id="avatarSpacingY"
                type="number"
                min="10"
                max="200"
                value={settings.avatarSpacingY || settings.avatarSpacing || 50}
                onChange={e => updateSettings({ avatarSpacingY: parseInt(e.target.value) || 50 })}
              />
            </div>
          </div>
        </div>

        <div className="pt-4 border-t">
          <div className="flex items-center justify-between">
            <div>
              <Label className="text-base">Avatar Assignment</Label>
              <p className="text-sm text-muted-foreground">Randomly reassign avatars to different positions</p>
            </div>
            <Button
              onClick={async () => {
                try {
                  const response = await fetch(`${apiUrl}/api/avatars/re-randomize`, { method: 'POST' })
                  const result = await response.json()
                  if (result.success) {
                    logger.info('✅ Avatar re-randomization triggered')
                  } else {
                    console.error('❌ Avatar re-randomization failed:', result.error)
                  }
                } catch (error) {
                  console.error('❌ Failed to trigger avatar re-randomization:', error)
                }
              }}
              variant="outline"
              size="sm"
            >
              🎲 Re-randomize Avatars
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default GeneralSettings