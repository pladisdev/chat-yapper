import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Switch } from '../ui/switch'
import { Slider } from '../ui/slider'
import { Separator } from '../ui/separator'
import { Music, Waves, TrendingUp, Zap, Shuffle } from 'lucide-react'
import logger from '../../utils/logger'

export default function AudioFiltersSettings({ settings, updateSettings }) {
  const audioFilters = settings.audioFilters || {
    enabled: false,
    randomFilters: false,
    reverb: { enabled: false, amount: 50, randomEnabled: true, randomRange: { min: 20, max: 80 } },
    pitch: { enabled: false, semitones: 0, randomEnabled: true, randomRange: { min: -8, max: 8 } },
    speed: { enabled: false, multiplier: 1.0, randomEnabled: true, randomRange: { min: 0.75, max: 1.3 } }
  }

  const updateFilter = (filterType, updates) => {
    const newFilters = {
      ...audioFilters,
      [filterType]: {
        ...audioFilters[filterType],
        ...updates
      }
    }
    updateSettings({ audioFilters: newFilters })
    logger.info(`Updated ${filterType} filter:`, updates)
  }

  const updateGlobalSetting = (key, value) => {
    const newFilters = {
      ...audioFilters,
      [key]: value
    }
    updateSettings({ audioFilters: newFilters })
    logger.info(`Updated audio filter setting ${key}:`, value)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Music className="w-5 h-5" />
          Effects
        </CardTitle>
        <CardDescription>
          Apply audio effects to TTS messages. Effects are processed on the server before playback.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Master Enable/Disable */}
        <div className="flex items-center justify-between p-4 border rounded-lg bg-muted/50">
          <div className="space-y-1">
            <Label className="text-base font-semibold">Enable Effects</Label>
            <p className="text-sm text-muted-foreground">
              Apply audio effects to all TTS messages
            </p>
          </div>
          <Switch
            checked={audioFilters.enabled}
            onCheckedChange={(checked) => updateGlobalSetting('enabled', checked)}
          />
        </div>

        {audioFilters.enabled && (
          <>
            {/* Random Effects */}
            <div className="flex items-center justify-between p-4 border rounded-lg bg-primary/5">
              <div className="space-y-1">
                <Label className="text-base font-semibold flex items-center gap-2">
                  <Shuffle className="w-4 h-4" />
                  Random Effect Mode
                </Label>
                <p className="text-sm text-muted-foreground">
                  Apply random combinations of effects with random values to each message for variety
                </p>
              </div>
              <Switch
                checked={audioFilters.randomFilters}
                onCheckedChange={(checked) => updateGlobalSetting('randomFilters', checked)}
              />
            </div>

            {!audioFilters.randomFilters && (
              <>
                <Separator />

                {/* Reverb Filter */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label className="text-base font-semibold flex items-center gap-2">
                        <Waves className="w-4 h-4" />
                        Reverb
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        Add spacial depth and echo effect
                      </p>
                    </div>
                    <Switch
                      checked={audioFilters.reverb.enabled}
                      onCheckedChange={(checked) => updateFilter('reverb', { enabled: checked })}
                    />
                  </div>

                  {audioFilters.reverb.enabled && (
                    <div className="space-y-2 ml-6">
                      <Label htmlFor="reverb-amount">Amount: {audioFilters.reverb.amount}%</Label>
                      <Slider
                        id="reverb-amount"
                        min={0}
                        max={100}
                        step={5}
                        value={[audioFilters.reverb.amount]}
                        onValueChange={([value]) => updateFilter('reverb', { amount: value })}
                        className="w-full"
                      />
                    </div>
                  )}
                </div>

                <Separator />

                {/* Pitch Shift Filter */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label className="text-base font-semibold flex items-center gap-2">
                        <TrendingUp className="w-4 h-4" />
                        Pitch Shift
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        Change voice pitch (higher or lower)
                      </p>
                    </div>
                    <Switch
                      checked={audioFilters.pitch.enabled}
                      onCheckedChange={(checked) => updateFilter('pitch', { enabled: checked })}
                    />
                  </div>

                  {audioFilters.pitch.enabled && (
                    <div className="space-y-2 ml-6">
                      <Label htmlFor="pitch-semitones">
                        Semitones: {audioFilters.pitch.semitones > 0 ? '+' : ''}{audioFilters.pitch.semitones}
                        {audioFilters.pitch.semitones === 0 && ' (no change)'}
                      </Label>
                      <Slider
                        id="pitch-semitones"
                        min={-12}
                        max={12}
                        step={1}
                        value={[audioFilters.pitch.semitones]}
                        onValueChange={([value]) => updateFilter('pitch', { semitones: value })}
                        className="w-full"
                      />
                      <p className="text-xs text-muted-foreground">
                        Negative = lower pitch, Positive = higher pitch
                      </p>
                    </div>
                  )}
                </div>

                <Separator />

                {/* Speed Filter */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label className="text-base font-semibold flex items-center gap-2">
                        <Zap className="w-4 h-4" />
                        Speed Change
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        Make audio faster or slower (affects duration)
                      </p>
                    </div>
                    <Switch
                      checked={audioFilters.speed.enabled}
                      onCheckedChange={(checked) => updateFilter('speed', { enabled: checked })}
                    />
                  </div>

                  {audioFilters.speed.enabled && (
                    <div className="space-y-2 ml-6">
                      <Label htmlFor="speed-multiplier">
                        Speed: {audioFilters.speed.multiplier.toFixed(2)}x
                        {audioFilters.speed.multiplier < 1 && ' (slower)'}
                        {audioFilters.speed.multiplier > 1 && ' (faster)'}
                      </Label>
                      <Slider
                        id="speed-multiplier"
                        min={50}
                        max={200}
                        step={5}
                        value={[audioFilters.speed.multiplier * 100]}
                        onValueChange={([value]) => updateFilter('speed', { multiplier: value / 100 })}
                        className="w-full"
                      />
                      <p className="text-xs text-muted-foreground">
                        0.5x = half speed, 2.0x = double speed
                      </p>
                    </div>
                  )}
                </div>
              </>
            )}

            {audioFilters.randomFilters && (
              <div className="space-y-4">
                <div className="p-4 border rounded-lg bg-muted/30 space-y-2">
                  <p className="text-sm font-medium">Random Mode Configuration</p>
                  <p className="text-sm text-muted-foreground">
                    Configure which effects can be randomly applied and their value ranges.
                  </p>
                </div>

                <Separator />

                {/* Random Reverb Settings */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label className="text-base font-semibold flex items-center gap-2">
                        <Waves className="w-4 h-4" />
                        Reverb (Random)
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        Enable reverb for random mode
                      </p>
                    </div>
                    <Switch
                      checked={audioFilters.reverb.randomEnabled !== false}
                      onCheckedChange={(checked) => updateFilter('reverb', { randomEnabled: checked })}
                    />
                  </div>

                  {audioFilters.reverb.randomEnabled !== false && (
                    <div className="space-y-4 ml-6">
                      <div className="space-y-2">
                        <Label>Amount Range: {audioFilters.reverb.randomRange?.min || 20}% - {audioFilters.reverb.randomRange?.max || 80}%</Label>
                        <div className="flex items-center gap-3">
                          <Label className="w-12 text-xs">Min:</Label>
                          <Slider
                            min={0}
                            max={100}
                            step={5}
                            value={[audioFilters.reverb.randomRange?.min || 20]}
                            onValueChange={([value]) => updateFilter('reverb', { 
                              randomRange: { ...audioFilters.reverb.randomRange, min: value }
                            })}
                            className="flex-1"
                          />
                          <span className="text-xs text-muted-foreground w-12">{audioFilters.reverb.randomRange?.min || 20}%</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <Label className="w-12 text-xs">Max:</Label>
                          <Slider
                            min={0}
                            max={100}
                            step={5}
                            value={[audioFilters.reverb.randomRange?.max || 80]}
                            onValueChange={([value]) => updateFilter('reverb', { 
                              randomRange: { ...audioFilters.reverb.randomRange, max: value }
                            })}
                            className="flex-1"
                          />
                          <span className="text-xs text-muted-foreground w-12">{audioFilters.reverb.randomRange?.max || 80}%</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <Separator />

                {/* Random Pitch Settings */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label className="text-base font-semibold flex items-center gap-2">
                        <TrendingUp className="w-4 h-4" />
                        Pitch Shift (Random)
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        Enable pitch shift for random mode
                      </p>
                    </div>
                    <Switch
                      checked={audioFilters.pitch.randomEnabled !== false}
                      onCheckedChange={(checked) => updateFilter('pitch', { randomEnabled: checked })}
                    />
                  </div>

                  {audioFilters.pitch.randomEnabled !== false && (
                    <div className="space-y-4 ml-6">
                      <div className="space-y-2">
                        <Label>Semitones Range: {audioFilters.pitch.randomRange?.min || -8} to {audioFilters.pitch.randomRange?.max || 8}</Label>
                        <div className="flex items-center gap-3">
                          <Label className="w-12 text-xs">Min:</Label>
                          <Slider
                            min={-12}
                            max={12}
                            step={1}
                            value={[audioFilters.pitch.randomRange?.min || -8]}
                            onValueChange={([value]) => updateFilter('pitch', { 
                              randomRange: { ...audioFilters.pitch.randomRange, min: value }
                            })}
                            className="flex-1"
                          />
                          <span className="text-xs text-muted-foreground w-12">{audioFilters.pitch.randomRange?.min || -8}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <Label className="w-12 text-xs">Max:</Label>
                          <Slider
                            min={-12}
                            max={12}
                            step={1}
                            value={[audioFilters.pitch.randomRange?.max || 8]}
                            onValueChange={([value]) => updateFilter('pitch', { 
                              randomRange: { ...audioFilters.pitch.randomRange, max: value }
                            })}
                            className="flex-1"
                          />
                          <span className="text-xs text-muted-foreground w-12">{audioFilters.pitch.randomRange?.max || 8}</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <Separator />

                {/* Random Speed Settings */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Label className="text-base font-semibold flex items-center gap-2">
                        <Zap className="w-4 h-4" />
                        Speed Change (Random)
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        Enable speed change for random mode
                      </p>
                    </div>
                    <Switch
                      checked={audioFilters.speed.randomEnabled !== false}
                      onCheckedChange={(checked) => updateFilter('speed', { randomEnabled: checked })}
                    />
                  </div>

                  {audioFilters.speed.randomEnabled !== false && (
                    <div className="space-y-4 ml-6">
                      <div className="space-y-2">
                        <Label>Speed Range: {(audioFilters.speed.randomRange?.min || 0.75).toFixed(2)}x - {(audioFilters.speed.randomRange?.max || 1.3).toFixed(2)}x</Label>
                        <div className="flex items-center gap-3">
                          <Label className="w-12 text-xs">Min:</Label>
                          <Slider
                            min={50}
                            max={200}
                            step={5}
                            value={[(audioFilters.speed.randomRange?.min || 0.75) * 100]}
                            onValueChange={([value]) => updateFilter('speed', { 
                              randomRange: { ...audioFilters.speed.randomRange, min: value / 100 }
                            })}
                            className="flex-1"
                          />
                          <span className="text-xs text-muted-foreground w-12">{(audioFilters.speed.randomRange?.min || 0.75).toFixed(2)}x</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <Label className="w-12 text-xs">Max:</Label>
                          <Slider
                            min={50}
                            max={200}
                            step={5}
                            value={[(audioFilters.speed.randomRange?.max || 1.3) * 100]}
                            onValueChange={([value]) => updateFilter('speed', { 
                              randomRange: { ...audioFilters.speed.randomRange, max: value / 100 }
                            })}
                            className="flex-1"
                          />
                          <span className="text-xs text-muted-foreground w-12">{(audioFilters.speed.randomRange?.max || 1.3).toFixed(2)}x</span>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            <div className="p-4 border border-yellow-500/20 rounded-lg bg-yellow-500/5 space-y-2">
              <p className="text-sm font-medium text-yellow-600 dark:text-yellow-400">
                Requirements
              </p>
              <p className="text-xs text-muted-foreground">
                Audio effects require <code className="bg-muted px-1 py-0.5 rounded">ffmpeg</code> to be installed on your system.
                Effects will be silently disabled if ffmpeg is not available.
              </p>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
