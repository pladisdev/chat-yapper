import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Button } from '../ui/button'
import { Switch } from '../ui/switch'
import { Settings, Sun, Moon, Plus, Minus, Infinity } from 'lucide-react'
import logger from '../../utils/logger'

function GeneralSettings({ settings, setSettings, updateSettings, apiUrl }) {
  const [tempVolume, setTempVolume] = useState(Math.round((settings.volume !== undefined ? settings.volume : 1.0) * 100))
  const [customLimit, setCustomLimit] = useState('')
  const [isCustomMode, setIsCustomMode] = useState(false)
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

  useEffect(() => {
    // Sync custom mode state with current settings
    const currentLimit = settings.parallelMessageLimit
    const presetValues = [1, 2, 3, 4, 5, 6, 8, 10, 15, 20, null]
    
    if (currentLimit !== null && !presetValues.includes(currentLimit)) {
      setIsCustomMode(true)
      setCustomLimit(currentLimit.toString())
    } else {
      setIsCustomMode(false)
      setCustomLimit('')
    }
  }, [settings.parallelMessageLimit])

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
        <CardDescription>Configure TTS control, audio volume, and message limits</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Label className="text-base">Dark/Light Mode</Label>
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
            <Label className="text-base">Font Size</Label>
          </div>
          <Button
            onClick={() => {
              const newSize = settings.textSize === 'large' ? 'normal' : 'large'
              updateSettings({ textSize: newSize })
              // Apply text size class globally to the html element
              if (newSize === 'large') {
                document.documentElement.classList.add('text-large')
              } else {
                document.documentElement.classList.remove('text-large')
              }
            }}
            variant="outline"
            size="sm"
            className="gap-2"
          >
            {settings.textSize === 'large' ? 'Large Text' : 'Normal Text'}
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

        <div className="space-y-3">
          <Label>Yapper Limit</Label>

          <p className="text-sm text-muted-foreground">
            Set the maximum number of messages that can be spoken simultaneously
          </p>
          
          <div className="flex items-center gap-4">
            {/* No Limit Toggle */}
            <Button
              onClick={() => {
                const isUnlimited = settings.parallelMessageLimit === null
                const newValue = isUnlimited ? 5 : null
                updateSettings({ parallelMessageLimit: newValue })
                logger.info(`Parallel message limit changed to ${isUnlimited ? '5' : 'unlimited'}`)
              }}
              variant={settings.parallelMessageLimit === null ? "default" : "outline"}
              className="gap-2 h-10"
            >
              <Infinity className="size-4" />
              No Limit
            </Button>
            
            {/* Button Group with Input and +/- Controls */}
            <div 
              role="group" 
              className="flex w-fit items-stretch [&>*]:focus-visible:z-10 [&>*]:focus-visible:relative [&>input]:flex-1 [&>*:not(:first-child)]:rounded-l-none [&>*:not(:first-child)]:border-l-0 [&>*:not(:last-child)]:rounded-r-none"
            >
              <Input
                type="number"
                min="1"
                max="999"
                value={settings.parallelMessageLimit === null ? '' : (settings.parallelMessageLimit || 5)}
                onChange={e => {
                  const value = e.target.value
                  if (value === '' || value === '0') {
                    // Don't update on empty or zero
                    return
                  }
                  const numValue = parseInt(value)
                  if (numValue >= 1 && numValue <= 999) {
                    updateSettings({ parallelMessageLimit: numValue })
                    logger.info(`Parallel message limit changed to ${numValue}`)
                  }
                }}
                placeholder="Inf"
                className="!w-20 font-mono text-center h-10 [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none [-moz-appearance:textfield]"
                disabled={settings.parallelMessageLimit === null}
              />
              
              <Button
                type="button"
                variant="outline"
                className="w-10 h-10 shrink-0"
                onClick={() => {
                  const current = settings.parallelMessageLimit
                  if (current === null) return // Can't decrement from unlimited
                  const newValue = Math.max(1, (current || 5) - 1)
                  updateSettings({ parallelMessageLimit: newValue })
                  logger.info(`Parallel message limit decreased to ${newValue}`)
                }}
                disabled={settings.parallelMessageLimit === null || settings.parallelMessageLimit <= 1}
                aria-label="Decrease limit"
              >
                <Minus className="size-4" />
              </Button>
              
              <Button
                type="button"
                variant="outline"
                className="w-10 h-10 shrink-0"
                onClick={() => {
                  const current = settings.parallelMessageLimit
                  if (current === null) return // Can't increment from unlimited
                  const newValue = Math.min(999, (current || 5) + 1)
                  updateSettings({ parallelMessageLimit: newValue })
                  logger.info(`Parallel message limit increased to ${newValue}`)
                }}
                disabled={settings.parallelMessageLimit === null || settings.parallelMessageLimit >= 999}
                aria-label="Increase limit"
              >
                <Plus className="size-4" />
              </Button>
            </div>
          </div>


          
          
        </div>

        <div className="flex items-center justify-between">
          <div>
            <Label htmlFor="queueOverflow" className="text-base">Queue Overflow Messages</Label>
            <p className="text-sm text-muted-foreground">
              When limit is reached, queue messages instead of ignoring them
            </p>
          </div>
          <Switch
            id="queueOverflow"
            checked={settings.queueOverflowMessages !== false}
            onCheckedChange={checked => {
              updateSettings({ queueOverflowMessages: checked })
              logger.info(`Queue overflow messages: ${checked ? 'enabled' : 'disabled'}`)
            }}
          />
        </div>
      </CardContent>
    </Card>
  )
}

export default GeneralSettings