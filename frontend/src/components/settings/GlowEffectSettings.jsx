import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Label } from '../ui/label'
import { Switch } from '../ui/switch'
import { Slider } from '../ui/slider'
import { Sparkles } from 'lucide-react'

export default function GlowEffectSettings({ settings, onUpdate }) {
  const glowEnabled = settings?.avatarGlowEnabled ?? true
  const glowColor = settings?.avatarGlowColor ?? '#ffffff'
  const glowOpacity = settings?.avatarGlowOpacity ?? 0.9
  const glowSize = settings?.avatarGlowSize ?? 20

  const handleToggle = async (enabled) => {
    await onUpdate({ avatarGlowEnabled: enabled })
  }

  const handleColorChange = async (e) => {
    await onUpdate({ avatarGlowColor: e.target.value })
  }

  const handleOpacityChange = async (value) => {
    await onUpdate({ avatarGlowOpacity: value[0] })
  }

  const handleSizeChange = async (value) => {
    await onUpdate({ avatarGlowSize: value[0] })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5" />
          Speaking Glow Effect
        </CardTitle>
        <CardDescription>
          Customize the visual glow effect applied to avatars when speaking
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Enable/Disable Toggle */}
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="glow-enabled">Enable Glow Effect</Label>
            <p className="text-sm text-muted-foreground">
              Show a glow effect when avatars are speaking
            </p>
          </div>
          <Switch
            id="glow-enabled"
            checked={glowEnabled}
            onCheckedChange={handleToggle}
          />
        </div>

        {/* Color Picker */}
        <div className="space-y-2">
          <Label htmlFor="glow-color">Glow Color</Label>
          <div className="flex items-center gap-3">
            <input
              id="glow-color"
              type="color"
              value={glowColor}
              onChange={handleColorChange}
              disabled={!glowEnabled}
              className="h-10 w-20 rounded border cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <input
              type="text"
              value={glowColor}
              onChange={handleColorChange}
              disabled={!glowEnabled}
              className="flex-1 px-3 py-2 text-sm border rounded bg-background disabled:opacity-50 disabled:cursor-not-allowed"
              placeholder="#ffffff"
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Choose the color of the glow effect around speaking avatars
          </p>
        </div>

        {/* Opacity Slider */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="glow-opacity">Glow Opacity</Label>
            <span className="text-sm text-muted-foreground">
              {Math.round(glowOpacity * 100)}%
            </span>
          </div>
          <Slider
            id="glow-opacity"
            min={0}
            max={1}
            step={0.05}
            value={[glowOpacity]}
            onValueChange={handleOpacityChange}
            disabled={!glowEnabled}
            className="w-full"
          />
          <p className="text-xs text-muted-foreground">
            Adjust the transparency of the glow effect (0% = invisible, 100% = fully opaque)
          </p>
        </div>

        {/* Size Slider */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="glow-size">Glow Size</Label>
            <span className="text-sm text-muted-foreground">
              {glowSize}px
            </span>
          </div>
          <Slider
            id="glow-size"
            min={0}
            max={50}
            step={1}
            value={[glowSize]}
            onValueChange={handleSizeChange}
            disabled={!glowEnabled}
            className="w-full"
          />
          <p className="text-xs text-muted-foreground">
            Adjust the spread/blur radius of the glow effect
          </p>
        </div>

        {/* Preview */}
        <div className="p-4 rounded-lg border bg-muted/30">
          <p className="text-xs text-muted-foreground mb-3">Preview:</p>
          <div className="flex justify-center">
            <div
              style={{
                width: '80px',
                height: '80px',
                borderRadius: '50%',
                backgroundColor: '#666',
                filter: glowEnabled
                  ? `brightness(1.25) drop-shadow(0 0 ${glowSize}px ${glowColor}${Math.round(glowOpacity * 255).toString(16).padStart(2, '0')})`
                  : 'drop-shadow(0 4px 8px rgba(0,0,0,0.3))',
                transition: 'filter 300ms ease-out'
              }}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
