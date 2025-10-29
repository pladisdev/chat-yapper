import React from 'react'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Button } from '../ui/button'
import logger from '../../utils/logger'

function AvatarPlacementSettings({ settings, updateSettings, apiUrl }) {
  return (
    <div className="space-y-6">
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
                  logger.info('Avatar re-randomization triggered')
                } else {
                  console.error('Avatar re-randomization failed:', result.error)
                }
              } catch (error) {
                console.error('Failed to trigger avatar re-randomization:', error)
              }
            }}
            variant="outline"
            size="sm"
          >
            Re-randomize Avatars
          </Button>
        </div>
      </div>
    </div>
  )
}

export default AvatarPlacementSettings
