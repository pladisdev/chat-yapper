import React, { useState } from 'react'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs'
import { Switch } from '../ui/switch'
import { Sparkles, Activity, Clock } from 'lucide-react'

function CrowdAnimationSettings({ settings, onUpdate }) {
  const animationSettings = {
    animationType: settings?.crowdAnimationType || 'bounce',
    bounceHeight: settings?.crowdBounceHeight ?? 10,
    animationDuration: settings?.crowdAnimationDuration ?? 300,
    animationDelay: settings?.crowdAnimationDelay ?? 0,
    animationCurve: settings?.crowdAnimationCurve || 'ease-out',
    // Idle animation settings
    idleAnimationType: settings?.crowdIdleAnimationType || 'none',
    idleAnimationIntensity: settings?.crowdIdleAnimationIntensity ?? 2,
    idleAnimationSpeed: settings?.crowdIdleAnimationSpeed ?? 3000,
    idleAnimationSynced: settings?.crowdIdleAnimationSynced ?? false
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Sparkles className="w-5 h-5" />
          Crowd Mode Animations
        </CardTitle>
        <CardDescription>
          Customize how avatars animate in crowd mode
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="active" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="active" className="flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Active Animations
            </TabsTrigger>
            <TabsTrigger value="idle" className="flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Idle Animations
            </TabsTrigger>
          </TabsList>

          <TabsContent value="active" className="mt-4 space-y-6">
            <div className="space-y-2">
              <Label htmlFor="animationType">Animation Type</Label>
              <select
                id="animationType"
                value={animationSettings.animationType}
                onChange={e => onUpdate({ crowdAnimationType: e.target.value })}
                className="w-full h-10 px-3 py-2 bg-background border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              >
                <option value="bounce">Bounce Up</option>
                <option value="spin">Spin</option>
                <option value="float">Float Up & Down</option>
                <option value="pulse">Pulse (Scale)</option>
                <option value="none">No Animation</option>
              </select>
              <p className="text-sm text-muted-foreground">
                The type of animation when an avatar is speaking
              </p>
            </div>

            {(animationSettings.animationType === 'bounce' || 
              animationSettings.animationType === 'float' || 
              animationSettings.animationType === 'spin') && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="bounceHeight">
                    {animationSettings.animationType === 'spin' ? 'Spin Distance' : 
                     animationSettings.animationType === 'bounce' ? 'Bounce Height' : 'Float Distance'} (px)
                  </Label>
                  <span className="text-sm text-muted-foreground">{animationSettings.bounceHeight}px</span>
                </div>
                <Input
                  id="bounceHeight"
                  type="range"
                  min="0"
                  max="50"
                  step="1"
                  value={animationSettings.bounceHeight}
                  onChange={e => onUpdate({ crowdBounceHeight: parseFloat(e.target.value) })}
                />
                <p className="text-sm text-muted-foreground">
                  {animationSettings.animationType === 'spin'
                    ? 'How far up the avatar moves while spinning'
                    : animationSettings.animationType === 'bounce' 
                    ? 'How far up the avatar bounces when active'
                    : 'Distance of the floating movement'}
                </p>
              </div>
            )}

            {animationSettings.animationType === 'pulse' && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="pulseScale">Pulse Scale (%)</Label>
                  <span className="text-sm text-muted-foreground">{animationSettings.bounceHeight}%</span>
                </div>
                <Input
                  id="pulseScale"
                  type="range"
                  min="100"
                  max="150"
                  step="5"
                  value={animationSettings.bounceHeight}
                  onChange={e => onUpdate({ crowdBounceHeight: parseFloat(e.target.value) })}
                />
                <p className="text-sm text-muted-foreground">
                  How much the avatar scales up when active (100% = no scaling)
                </p>
              </div>
            )}

            {animationSettings.animationType === 'bounce' && (
              <div className="space-y-2">
                <Label htmlFor="animationCurve">Animation Curve</Label>
                <select
                  id="animationCurve"
                  value={animationSettings.animationCurve}
                  onChange={e => onUpdate({ crowdAnimationCurve: e.target.value })}
                  className="w-full h-10 px-3 py-2 bg-background border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                >
                  <option value="ease-out">Ease Out (Default)</option>
                  <option value="ease-in">Ease In</option>
                  <option value="ease-in-out">Ease In-Out</option>
                  <option value="linear">Linear</option>
                  <option value="bounce">Bouncy</option>
                  <option value="elastic">Elastic</option>
                </select>
                <p className="text-sm text-muted-foreground">
                  The timing curve for the bounce animation
                </p>
              </div>
            )}

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="animationDuration">Animation Duration (ms)</Label>
                <span className="text-sm text-muted-foreground">{animationSettings.animationDuration}ms</span>
              </div>
              <Input
                id="animationDuration"
                type="range"
                min="100"
                max="1000"
                step="50"
                value={animationSettings.animationDuration}
                onChange={e => onUpdate({ crowdAnimationDuration: parseInt(e.target.value) })}
              />
              <p className="text-sm text-muted-foreground">
                Speed of the animation transition
              </p>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="animationDelay">Animation Delay (ms)</Label>
                <span className="text-sm text-muted-foreground">{animationSettings.animationDelay}ms</span>
              </div>
              <Input
                id="animationDelay"
                type="range"
                min="0"
                max="500"
                step="50"
                value={animationSettings.animationDelay}
                onChange={e => onUpdate({ crowdAnimationDelay: parseInt(e.target.value) })}
              />
              <p className="text-sm text-muted-foreground">
                Delay before the animation starts when avatar becomes active
              </p>
            </div>

            <div className="p-4 bg-muted rounded-lg">
              <h4 className="text-sm font-medium mb-2">Active Animation Preview</h4>
              <div className="text-sm text-muted-foreground space-y-1">
                <p>• Type: <span className="font-medium text-foreground">{animationSettings.animationType}</span></p>
                {animationSettings.animationType !== 'none' && (
                  <>
                    <p>• {animationSettings.animationType === 'pulse' ? 'Scale' : 'Height'}: <span className="font-medium text-foreground">{animationSettings.bounceHeight}{animationSettings.animationType === 'pulse' ? '%' : 'px'}</span></p>
                    {animationSettings.animationType === 'bounce' && (
                      <p>• Curve: <span className="font-medium text-foreground">{animationSettings.animationCurve}</span></p>
                    )}
                    <p>• Duration: <span className="font-medium text-foreground">{animationSettings.animationDuration}ms</span></p>
                    <p>• Delay: <span className="font-medium text-foreground">{animationSettings.animationDelay}ms</span></p>
                  </>
                )}
              </div>
            </div>
          </TabsContent>

          <TabsContent value="idle" className="mt-4 space-y-6">
            <div className="space-y-2">
              <Label htmlFor="idleAnimationType">Idle Animation Type</Label>
              <select
                id="idleAnimationType"
                value={animationSettings.idleAnimationType}
                onChange={e => onUpdate({ crowdIdleAnimationType: e.target.value })}
                className="w-full h-10 px-3 py-2 bg-background border border-input rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              >
                <option value="none">None</option>
                <option value="jitter">Jitter (Vibrate)</option>
                <option value="pulse">Pulse (Scale In & Out)</option>
                <option value="sway-horizontal">Sway Left & Right</option>
                <option value="sway-vertical">Sway Up & Down</option>
              </select>
              <p className="text-sm text-muted-foreground">
                Animation for avatars when they are not speaking
              </p>
            </div>

            {animationSettings.idleAnimationType !== 'none' && (
              <>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="idleIntensity">Intensity</Label>
                    <span className="text-sm text-muted-foreground">
                      {animationSettings.idleAnimationIntensity <= 3 ? 'Subtle' : 
                       animationSettings.idleAnimationIntensity <= 6 ? 'Medium' : 'Strong'}
                    </span>
                  </div>
                  <Input
                    id="idleIntensity"
                    type="range"
                    min="1"
                    max="10"
                    step="1"
                    value={animationSettings.idleAnimationIntensity}
                    onChange={e => onUpdate({ crowdIdleAnimationIntensity: parseFloat(e.target.value) })}
                  />
                  <p className="text-sm text-muted-foreground">
                    {animationSettings.idleAnimationType === 'jitter' ? 'How much the avatar vibrates' :
                     animationSettings.idleAnimationType === 'pulse' ? 'How much the avatar scales' :
                     'How far the avatar moves'}
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="idleSpeed">Animation Speed (ms)</Label>
                    <span className="text-sm text-muted-foreground">{animationSettings.idleAnimationSpeed}ms</span>
                  </div>
                  <Input
                    id="idleSpeed"
                    type="range"
                    min="1000"
                    max="5000"
                    step="500"
                    value={animationSettings.idleAnimationSpeed}
                    onChange={e => onUpdate({ crowdIdleAnimationSpeed: parseInt(e.target.value) })}
                  />
                  <p className="text-sm text-muted-foreground">
                    Duration of one animation cycle (lower = faster)
                  </p>
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="idleAnimationSynced">Synchronized Animations</Label>
                    <p className="text-sm text-muted-foreground">
                      All avatars animate in sync vs. independently
                    </p>
                  </div>
                  <Switch
                    id="idleAnimationSynced"
                    checked={animationSettings.idleAnimationSynced}
                    onCheckedChange={checked => onUpdate({ crowdIdleAnimationSynced: checked })}
                  />
                </div>

                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="text-sm font-medium mb-2">Idle Animation Preview</h4>
                  <div className="text-sm text-muted-foreground space-y-1">
                    <p>• Type: <span className="font-medium text-foreground">{animationSettings.idleAnimationType}</span></p>
                    <p>• Intensity: <span className="font-medium text-foreground">
                      {animationSettings.idleAnimationIntensity <= 3 ? 'Subtle' : 
                       animationSettings.idleAnimationIntensity <= 6 ? 'Medium' : 'Strong'}
                    </span></p>
                    <p>• Speed: <span className="font-medium text-foreground">{animationSettings.idleAnimationSpeed}ms</span></p>
                    <p>• Sync: <span className="font-medium text-foreground">{animationSettings.idleAnimationSynced ? 'Synchronized' : 'Independent'}</span></p>
                  </div>
                </div>
              </>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

export default CrowdAnimationSettings
