import React from 'react'
import { Label } from '../ui/label'
import { Switch } from '../ui/switch'
import { Slider } from '../ui/slider'
import { Input } from '../ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { MessageSquare } from 'lucide-react'
import { hexColorWithOpacity } from '../../utils/colorUtils'

const FONT_OPTIONS = [
  { value: 'Arial, sans-serif', label: 'Arial' },
  { value: '"Helvetica Neue", Helvetica, sans-serif', label: 'Helvetica' },
  { value: '"Segoe UI", Tahoma, sans-serif', label: 'Segoe UI' },
  { value: 'Verdana, sans-serif', label: 'Verdana' },
  { value: '"Trebuchet MS", sans-serif', label: 'Trebuchet MS' },
  { value: 'Georgia, serif', label: 'Georgia' },
  { value: '"Times New Roman", Times, serif', label: 'Times New Roman' },
  { value: '"Courier New", Courier, monospace', label: 'Courier New' },
  { value: '"Comic Sans MS", cursive', label: 'Comic Sans MS' },
  { value: 'Impact, fantasy', label: 'Impact' },
  { value: '"Brush Script MT", cursive', label: 'Brush Script' }
]

function ChatBubbleSettings({ settings, onUpdate }) {
  const chatBubblesEnabled = settings?.chatBubblesEnabled ?? true
  const bubbleFontFamily = settings?.bubbleFontFamily ?? 'Arial, sans-serif'
  const bubbleFontSize = settings?.bubbleFontSize ?? 14
  const bubbleFontColor = settings?.bubbleFontColor ?? '#ffffff'
  const bubbleBackgroundColor = settings?.bubbleBackgroundColor ?? '#000000'
  const bubbleOpacity = settings?.bubbleOpacity ?? 0.85
  const bubbleRounded = settings?.bubbleRounded ?? true

  const handleToggle = (enabled) => {
    onUpdate({ chatBubblesEnabled: enabled })
  }

  const handleFontFamilyChange = (e) => {
    onUpdate({ bubbleFontFamily: e.target.value })
  }

  const handleFontSizeChange = (value) => {
    onUpdate({ bubbleFontSize: value[0] })
  }

  const handleFontColorChange = (e) => {
    onUpdate({ bubbleFontColor: e.target.value })
  }

  const handleBackgroundColorChange = (e) => {
    onUpdate({ bubbleBackgroundColor: e.target.value })
  }

  const handleOpacityChange = (value) => {
    onUpdate({ bubbleOpacity: value[0] })
  }

  const handleRoundedToggle = (rounded) => {
    onUpdate({ bubbleRounded: rounded })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <MessageSquare className="w-5 h-5" />
          Chat Bubbles
        </CardTitle>
        <CardDescription>
          Display chat messages in speech bubbles above avatars
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label htmlFor="chatBubbles-enabled" className="text-base">
              Enable Chat Bubbles
            </Label>
          </div>
          <Switch
            id="chatBubbles-enabled"
            checked={chatBubblesEnabled}
            onCheckedChange={handleToggle}
          />
        </div>

        {chatBubblesEnabled && (
          <>
            {/* Font Family */}
            <div className="space-y-2">
              <Label htmlFor="bubble-font" className="text-sm font-medium">
                Font Family
              </Label>
              <select
                id="bubble-font"
                value={bubbleFontFamily}
                onChange={handleFontFamilyChange}
                className="w-full h-10 px-3 py-2 bg-background border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              >
                {FONT_OPTIONS.map(font => (
                  <option key={font.value} value={font.value}>
                    {font.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Font Size */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="bubble-font-size" className="text-sm font-medium">
                  Font Size
                </Label>
                <span className="text-sm text-muted-foreground">{bubbleFontSize}px</span>
              </div>
              <Slider
                id="bubble-font-size"
                min={10}
                max={24}
                step={1}
                value={[bubbleFontSize]}
                onValueChange={handleFontSizeChange}
              />
            </div>

            {/* Font Color */}
            <div className="space-y-2">
              <Label htmlFor="bubble-font-color" className="text-sm font-medium">
                Font Color
              </Label>
              <div className="flex items-center gap-2">
                <Input
                  id="bubble-font-color"
                  type="color"
                  value={bubbleFontColor}
                  onChange={handleFontColorChange}
                  className="w-20 h-10 cursor-pointer"
                />
                <Input
                  type="text"
                  value={bubbleFontColor}
                  onChange={handleFontColorChange}
                  className="flex-1"
                  placeholder="#ffffff"
                />
              </div>
            </div>

            {/* Background Color */}
            <div className="space-y-2">
              <Label htmlFor="bubble-bg-color" className="text-sm font-medium">
                Background Color
              </Label>
              <div className="flex items-center gap-2">
                <Input
                  id="bubble-bg-color"
                  type="color"
                  value={bubbleBackgroundColor}
                  onChange={handleBackgroundColorChange}
                  className="w-20 h-10 cursor-pointer"
                />
                <Input
                  type="text"
                  value={bubbleBackgroundColor}
                  onChange={handleBackgroundColorChange}
                  className="flex-1"
                  placeholder="#000000"
                />
              </div>
            </div>

            {/* Opacity */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="bubble-opacity" className="text-sm font-medium">
                  Opacity
                </Label>
                <span className="text-sm text-muted-foreground">{Math.round(bubbleOpacity * 100)}%</span>
              </div>
              <Slider
                id="bubble-opacity"
                min={0}
                max={1}
                step={0.05}
                value={[bubbleOpacity]}
                onValueChange={handleOpacityChange}
              />
            </div>

            {/* Shape Toggle */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="bubble-rounded" className="text-sm font-medium">
                  Rounded Corners
                </Label>
              </div>
              <Switch
                id="bubble-rounded"
                checked={bubbleRounded}
                onCheckedChange={handleRoundedToggle}
              />
            </div>
          </>
        )}

        {/* Preview */}
        <div className="flex justify-center py-6">
          <div className="relative inline-block">
            {/* Example avatar */}
            <div className="w-12 h-12 rounded-full bg-primary/20 flex items-center justify-center">
              <MessageSquare className="w-6 h-6 text-primary" />
            </div>
            {/* Example chat bubble */}
            {chatBubblesEnabled && (
              <div 
                className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 whitespace-nowrap"
                style={{
                  backgroundColor: hexColorWithOpacity(bubbleBackgroundColor, bubbleOpacity),
                  borderRadius: bubbleRounded ? '12px' : '4px',
                  fontFamily: bubbleFontFamily,
                  fontSize: `${bubbleFontSize}px`,
                  color: bubbleFontColor,
                  lineHeight: '1.4'
                }}
              >
                Hello, World!
                <div 
                  className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0"
                  style={{
                    borderLeft: '6px solid transparent',
                    borderRight: '6px solid transparent',
                    borderTop: `6px solid ${hexColorWithOpacity(bubbleBackgroundColor, bubbleOpacity)}`
                  }}
                />
              </div>
            )}
          </div>
        </div>

      </CardContent>
    </Card>
  )
}

export default ChatBubbleSettings
