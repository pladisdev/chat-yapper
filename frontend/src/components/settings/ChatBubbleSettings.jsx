import React, { useState, useEffect } from 'react'
import { Label } from '../ui/label'
import { Switch } from '../ui/switch'
import { Slider } from '../ui/slider'
import { Input } from '../ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { MessageSquare, RefreshCw } from 'lucide-react'
import { hexColorWithOpacity } from '../../utils/colorUtils'

const DEFAULT_FONT_OPTIONS = [
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
  { value: '"Brush Script MT", cursive', label: 'Brush Script' },
  { value: 'custom', label: 'Custom Font...' }
]

function ChatBubbleSettings({ settings, onUpdate }) {
  const chatBubblesEnabled = settings?.chatBubblesEnabled ?? true
  const bubbleFontFamily = settings?.bubbleFontFamily ?? 'Arial, sans-serif'
  
  // State for system fonts
  const [systemFonts, setSystemFonts] = useState([])
  const [loadingFonts, setLoadingFonts] = useState(false)
  const [fontOptions, setFontOptions] = useState(DEFAULT_FONT_OPTIONS)
  
  // Determine if current font is custom (not in the preset list)
  const isCustomFont = !fontOptions.slice(0, -1).some(opt => opt.value === bubbleFontFamily)
  const [showCustomInput, setShowCustomInput] = useState(isCustomFont)
  const [customFontValue, setCustomFontValue] = useState(isCustomFont ? bubbleFontFamily : '')
  const bubbleFontSize = settings?.bubbleFontSize ?? 14
  const bubbleFontColor = settings?.bubbleFontColor ?? '#ffffff'
  const bubbleBackgroundColor = settings?.bubbleBackgroundColor ?? '#000000'
  const bubbleOpacity = settings?.bubbleOpacity ?? 0.85
  const bubbleRounded = settings?.bubbleRounded ?? true
  const bubbleShowUsername = settings?.bubbleShowUsername ?? true
  const bubbleUsernameColor = settings?.bubbleUsernameColor ?? '#ffffff'

  // Load system fonts on component mount
  useEffect(() => {
    loadSystemFonts()
  }, [])

  /**
   * Check if a font is actually available in the browser
   * Uses canvas-based font detection
   */
  const isFontAvailable = (fontName) => {
    // Create a test string
    const testString = "mmmmmmmmmmlli"
    const testSize = '72px'
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')
    
    // Get baseline width using a common fallback font
    context.font = `${testSize} monospace`
    const baselineWidth = context.measureText(testString).width
    
    // Test with the font in question, with monospace as fallback
    context.font = `${testSize} ${fontName}, monospace`
    const testWidth = context.measureText(testString).width
    
    // If widths differ, the font is available (not falling back to monospace)
    return testWidth !== baselineWidth
  }

  /**
   * Filter fonts to only those available in the browser
   */
  const filterAvailableFonts = (fonts) => {
    const available = []
    
    for (const font of fonts) {
      // Extract the main font name from the family string
      // e.g., '"Arial Black", sans-serif' -> 'Arial Black'
      const fontName = font.family.split(',')[0].replace(/['"]/g, '').trim()
      
      if (isFontAvailable(fontName)) {
        available.push(font)
      }
    }
    
    return available
  }

  const loadSystemFonts = async () => {
    setLoadingFonts(true)
    try {
      const response = await fetch('/api/system/fonts')
      const data = await response.json()
      
      if (data.fonts && data.fonts.length > 0) {
        // Filter to only fonts that actually work in the browser
        const availableFonts = filterAvailableFonts(data.fonts)
        
        console.log(`Detected ${data.fonts.length} system fonts, ${availableFonts.length} available in browser`)
        
        // Convert available fonts to option format
        const systemFontOptions = availableFonts.map(font => ({
          value: font.family,
          label: font.name
        }))
        
        // Combine system fonts with custom option at the end
        setFontOptions([...systemFontOptions, { value: 'custom', label: 'Custom Font...' }])
        setSystemFonts(availableFonts)
      }
    } catch (error) {
      console.error('Failed to load system fonts:', error)
      // Keep default fonts if loading fails
    } finally {
      setLoadingFonts(false)
    }
  }

  const handleToggle = (enabled) => {
    onUpdate({ chatBubblesEnabled: enabled })
  }

  const handleFontFamilyChange = (e) => {
    const value = e.target.value
    if (value === 'custom') {
      setShowCustomInput(true)
      // Don't update the font yet, wait for user to type in the custom input
    } else {
      setShowCustomInput(false)
      setCustomFontValue('')
      onUpdate({ bubbleFontFamily: value })
    }
  }

  const handleCustomFontChange = (e) => {
    const value = e.target.value
    setCustomFontValue(value)
    if (value.trim()) {
      onUpdate({ bubbleFontFamily: value })
    }
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

  const handleShowUsernameToggle = (show) => {
    onUpdate({ bubbleShowUsername: show })
  }

  const handleUsernameColorChange = (e) => {
    onUpdate({ bubbleUsernameColor: e.target.value })
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
              <div className="flex items-center justify-between">
                <Label htmlFor="bubble-font" className="text-sm font-medium">
                  Font Family
                </Label>
                {systemFonts.length > 0 && (
                  <button
                    onClick={loadSystemFonts}
                    disabled={loadingFonts}
                    className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
                    title="Refresh system fonts"
                  >
                    <RefreshCw className={`w-3 h-3 ${loadingFonts ? 'animate-spin' : ''}`} />
                    {loadingFonts ? 'Loading...' : `${systemFonts.length} fonts`}
                  </button>
                )}
              </div>
              <select
                id="bubble-font"
                value={showCustomInput ? 'custom' : bubbleFontFamily}
                onChange={handleFontFamilyChange}
                className="w-full h-10 px-3 py-2 bg-background border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              >
                {fontOptions.map(font => (
                  <option key={font.value} value={font.value}>
                    {font.label}
                  </option>
                ))}
              </select>
              {showCustomInput && (
                <div className="mt-2">
                  <Input
                    type="text"
                    placeholder="Enter font name (e.g., 'Roboto, sans-serif' or 'MyCustomFont')"
                    value={customFontValue}
                    onChange={handleCustomFontChange}
                    className="w-full"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Enter any system font name or web font family. Include fallbacks for best compatibility.
                  </p>
                </div>
              )}
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

            {/* Show Username Toggle */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="bubble-show-username" className="text-sm font-medium">
                  Show Username
                </Label>
                <p className="text-xs text-muted-foreground">
                  Display the user's name above the message
                </p>
              </div>
              <Switch
                id="bubble-show-username"
                checked={bubbleShowUsername}
                onCheckedChange={handleShowUsernameToggle}
              />
            </div>

            {/* Username Color */}
            {bubbleShowUsername && (
              <div className="space-y-2">
                <Label htmlFor="bubble-username-color" className="text-sm font-medium">
                  Username Color
                </Label>
                <div className="flex items-center gap-2">
                  <Input
                    id="bubble-username-color"
                    type="color"
                    value={bubbleUsernameColor}
                    onChange={handleUsernameColorChange}
                    className="w-20 h-10 cursor-pointer"
                  />
                  <Input
                    type="text"
                    value={bubbleUsernameColor}
                    onChange={handleUsernameColorChange}
                    className="flex-1"
                    placeholder="#ffffff"
                  />
                </div>
              </div>
            )}

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
                className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2"
                style={{
                  minWidth: '120px'
                }}
              >
                {bubbleShowUsername && (
                  <div 
                    className="px-2 py-0.5 mb-0.5"
                    style={{
                      fontFamily: bubbleFontFamily,
                      fontSize: `${Math.max(10, bubbleFontSize - 2)}px`,
                      color: bubbleUsernameColor,
                      fontWeight: '600',
                      opacity: 0.9
                    }}
                  >
                    Username
                  </div>
                )}
                <div 
                  className="px-3 py-2 whitespace-nowrap"
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
              </div>
            )}
          </div>
        </div>

      </CardContent>
    </Card>
  )
}

export default ChatBubbleSettings
