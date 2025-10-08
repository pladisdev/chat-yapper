import React, { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Switch } from '../components/ui/switch'
import { Button } from '../components/ui/button'
import { Checkbox } from '../components/ui/checkbox'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { Separator } from '../components/ui/separator'
import { useWebSocket } from '../WebSocketContext'
import VoiceManager from '../components/VoiceManager'
import { 
  Settings, 
  Image, 
  Mic, 
  Zap, 
  MessageSquare, 
  TestTube2, 
  BarChart3,
  CheckCircle2,
  XCircle
} from 'lucide-react'

export default function SettingsPage() {
  const [settings, setSettings] = useState(null)
  const [allVoices, setAllVoices] = useState([])
  const [managedAvatars, setManagedAvatars] = useState([])
  const [uploading, setUploading] = useState(false)
  const [uploadMode, setUploadMode] = useState('single')
  const [selectedAvatarGroup, setSelectedAvatarGroup] = useState('')
  const [avatarName, setAvatarName] = useState('')
  const [lastUploadedName, setLastUploadedName] = useState('')
  const { addListener } = useWebSocket()

  // Determine the correct API URL
  const apiUrl = location.hostname === 'localhost' && (location.port === '5173' || location.port === '5174')
    ? 'http://localhost:8000'
    : ''

  useEffect(() => {
    // Load settings
    fetch(`${apiUrl}/api/settings`).then(r => r.json()).then(data => {
      setSettings(data)
    })
    
    // Load voices from database
    fetch(`${apiUrl}/api/voices`).then(r => r.json()).then(data => {
      setAllVoices(data?.voices || [])
    })
    
    // Load managed avatars
    fetch(`${apiUrl}/api/avatars/managed`).then(r => r.json()).then(data => {
      setManagedAvatars(data?.avatars || [])
    })
  }, [apiUrl])

  // WebSocket listener for TTS control updates
  useEffect(() => {
    const removeListener = addListener((data) => {
      if (data.type === 'tts_global_stopped') {
        console.log('🔇 TTS globally stopped via WebSocket')
        setSettings(prevSettings => ({
          ...prevSettings,
          ttsControl: { enabled: false }
        }))
      } else if (data.type === 'tts_global_resumed') {
        console.log('🔊 TTS globally resumed via WebSocket')
        setSettings(prevSettings => ({
          ...prevSettings,
          ttsControl: { enabled: true }
        }))
      }
    })

    return removeListener
  }, [addListener])

  const updateSettings = async (partial) => {
    const next = { ...(settings || {}), ...partial }
    setSettings(next)
    await fetch(`${apiUrl}/api/settings`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(next) })
  }

  const simulate = async (user, text, eventType='chat') => {
    console.log('🧪 Sending test message:', { user, text, eventType })
    const fd = new FormData()
    fd.set('user', user)
    fd.set('text', text)
    fd.set('eventType', eventType)
    
    try {
      const response = await fetch(`${apiUrl}/api/simulate`, { method: 'POST', body: fd })
      const result = await response.json()
      console.log('✅ Simulate response:', result)
    } catch (error) {
      console.error('❌ Simulate error:', error)
    }
  }

  const checkForReplacement = (avatarName, avatarType) => {
    const existing = managedAvatars.find(a => a.name === avatarName && a.avatar_type === avatarType)
    return existing ? { 
      exists: true, 
      avatar: existing, 
      message: `This will replace the existing ${avatarType} image for "${avatarName}"` 
    } : { exists: false }
  }

  const handleAvatarUpload = async (event, avatarType = 'default') => {
    const file = event.target.files[0]
    if (!file) return

    if (!avatarName.trim()) {
      alert('Please enter an avatar name first')
      return
    }

    const replacementCheck = checkForReplacement(avatarName.trim(), avatarType)
    if (replacementCheck.exists) {
      if (!confirm(`${replacementCheck.message}\n\nDo you want to continue and replace the existing image?`)) {
        return
      }
    }

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('avatar_name', avatarName.trim())
      formData.append('avatar_type', avatarType)
      
      if (uploadMode === 'pair') {
        // If the name changed, clear the group to start a new pair
        const currentName = avatarName.trim()
        if (lastUploadedName && lastUploadedName !== currentName) {
          setSelectedAvatarGroup('')
        }
        
        const groupId = selectedAvatarGroup || `avatar_${Date.now()}`
        formData.append('avatar_group_id', groupId)
        if (!selectedAvatarGroup) {
          setSelectedAvatarGroup(groupId)
        }
        setLastUploadedName(currentName)
      }
      
      const response = await fetch(`${apiUrl}/api/avatars/upload`, {
        method: 'POST',
        body: formData
      })
      
      const result = await response.json()
      if (result.success) {
        const avatarsResponse = await fetch(`${apiUrl}/api/avatars/managed`)
        const avatarsData = await avatarsResponse.json()
        setManagedAvatars(avatarsData?.avatars || [])
        
        if (uploadMode === 'single') {
          setAvatarName('')
          setLastUploadedName('')
        }
      } else {
        alert(`Upload failed: ${result.error}`)
      }
    } catch (error) {
      alert(`Upload error: ${error.message}`)
    } finally {
      setUploading(false)
      event.target.value = ''
    }
  }

  const handleDeleteAvatar = async (avatarId) => {
    if (!confirm('Are you sure you want to delete this avatar?')) return

    try {
      const response = await fetch(`${apiUrl}/api/avatars/${avatarId}`, {
        method: 'DELETE'
      })
      
      const result = await response.json()
      if (result.success) {
        const avatarsResponse = await fetch(`${apiUrl}/api/avatars/managed`)
        const avatarsData = await avatarsResponse.json()
        setManagedAvatars(avatarsData?.avatars || [])
      } else {
        alert(`Delete failed: ${result.error}`)
      }
    } catch (error) {
      alert(`Delete error: ${error.message}`)
    }
  }

  const handleDeleteAvatarGroup = async (groupId, avatarName, isPair) => {
    const confirmText = isPair 
      ? `Are you sure you want to delete the avatar pair "${avatarName}"? This will delete both the default and speaking images.`
      : `Are you sure you want to delete the avatar "${avatarName}"?`
    
    if (!confirm(confirmText)) return

    try {
      const response = await fetch(`${apiUrl}/api/avatars/group/${encodeURIComponent(groupId)}`, {
        method: 'DELETE'
      })
      
      const result = await response.json()
      if (result.success) {
        const avatarsResponse = await fetch(`${apiUrl}/api/avatars/managed`)
        const avatarsData = await avatarsResponse.json()
        setManagedAvatars(avatarsData?.avatars || [])
      } else {
        alert(`Delete failed: ${result.error}`)
      }
    } catch (error) {
      alert(`Delete error: ${error.message}`)
    }
  }

  if (!settings) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-3">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          <span className="text-lg">Loading settings...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="space-y-2">
          <h1 className="text-4xl font-bold flex items-center gap-3">
            <Settings className="w-10 h-10" />
            Chat Yapper Settings
          </h1>
          <p className="text-muted-foreground">Configure your voice avatar TTS system</p>
        </div>

        <Tabs defaultValue="general" className="space-y-6">
          <TabsList className="grid w-full grid-cols-6 lg:w-auto lg:inline-grid">
            <TabsTrigger value="general" className="flex items-center gap-2">
              <Settings className="w-4 h-4" />
              <span className="hidden sm:inline">General</span>
            </TabsTrigger>
            <TabsTrigger value="avatars" className="flex items-center gap-2">
              <Image className="w-4 h-4" />
              <span className="hidden sm:inline">Avatars</span>
            </TabsTrigger>
            <TabsTrigger value="tts" className="flex items-center gap-2">
              <Mic className="w-4 h-4" />
              <span className="hidden sm:inline">TTS</span>
            </TabsTrigger>
            <TabsTrigger value="twitch" className="flex items-center gap-2">
              <Zap className="w-4 h-4" />
              <span className="hidden sm:inline">Twitch</span>
            </TabsTrigger>
            <TabsTrigger value="filtering" className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              <span className="hidden sm:inline">Filtering</span>
            </TabsTrigger>
            <TabsTrigger value="test" className="flex items-center gap-2">
              <TestTube2 className="w-4 h-4" />
              <span className="hidden sm:inline">Test</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="general" className="space-y-6">
            <GeneralSettings settings={settings} updateSettings={updateSettings} apiUrl={apiUrl} />
          </TabsContent>

          <TabsContent value="avatars" className="space-y-6">
            <AvatarManagement
              managedAvatars={managedAvatars}
              apiUrl={apiUrl}
              avatarName={avatarName}
              setAvatarName={setAvatarName}
              uploadMode={uploadMode}
              setUploadMode={setUploadMode}
              uploading={uploading}
              checkForReplacement={checkForReplacement}
              handleAvatarUpload={handleAvatarUpload}
              handleDeleteAvatar={handleDeleteAvatar}
              handleDeleteAvatarGroup={handleDeleteAvatarGroup}
              selectedAvatarGroup={selectedAvatarGroup}
              setSelectedAvatarGroup={setSelectedAvatarGroup}
              lastUploadedName={lastUploadedName}
              setLastUploadedName={setLastUploadedName}
              allVoices={allVoices}
              settings={settings}
              setManagedAvatars={setManagedAvatars}
            />
          </TabsContent>

          <TabsContent value="tts" className="space-y-6">
            <TTSConfiguration settings={settings} updateSettings={updateSettings} />
            <VoiceManager managedAvatars={managedAvatars} apiUrl={apiUrl} />
          </TabsContent>

          <TabsContent value="twitch" className="space-y-6">
            <TwitchIntegration settings={settings} updateSettings={updateSettings} />
            <SpecialEventVoices settings={settings} updateSettings={updateSettings} allVoices={allVoices} />
          </TabsContent>

          <TabsContent value="filtering" className="space-y-6">
            <MessageFiltering settings={settings} updateSettings={updateSettings} apiUrl={apiUrl} />
          </TabsContent>

          <TabsContent value="test" className="space-y-6">
            <Simulator onSend={simulate} />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

// Sub-components would be imported from separate files in a real app
// For now, including them inline for completeness

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
                  console.log(`✅ TTS ${result.tts_enabled ? 'enabled' : 'disabled'}`)
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
                    console.log('✅ Avatar re-randomization triggered')
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

function TwitchIntegration({ settings, updateSettings }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-purple-500" />
          Twitch Integration
        </CardTitle>
        <CardDescription>Connect to your Twitch chat for live TTS</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
          <div className="space-y-1">
            <Label htmlFor="twitch-enabled" className="text-base">Enable Twitch Bot</Label>
            <p className="text-sm text-muted-foreground">Connect to your Twitch chat</p>
          </div>
          <Switch
            id="twitch-enabled"
            checked={!!settings.twitch?.enabled}
            onCheckedChange={checked => updateSettings({ twitch: { ...settings.twitch, enabled: checked } })}
          />
        </div>

        {settings.twitch?.enabled && (
          <div className="space-y-4">
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="channel">Channel Name</Label>
                <Input
                  id="channel"
                  placeholder="your_channel_name"
                  value={settings.twitch?.channel || ''}
                  onChange={e => updateSettings({ twitch: { ...settings.twitch, channel: e.target.value } })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="nick">Bot Nickname</Label>
                <Input
                  id="nick"
                  placeholder="your_bot_username"
                  value={settings.twitch?.nick || ''}
                  onChange={e => updateSettings({ twitch: { ...settings.twitch, nick: e.target.value } })}
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="token">OAuth Token</Label>
              <Input
                id="token"
                type="password"
                placeholder="oauth:your_token_here"
                value={settings.twitch?.token || ''}
                onChange={e => updateSettings({ twitch: { ...settings.twitch, token: e.target.value } })}
              />
              <p className="text-sm text-muted-foreground">
                Get your OAuth token at{' '}
                <a href="https://twitchtokengenerator.com/" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                  twitchtokengenerator.com
                </a>
                {' '}with "chat:read" scope
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Continuing in next part due to size...
function AvatarManagement({
  managedAvatars,
  apiUrl,
  avatarName,
  setAvatarName,
  uploadMode,
  setUploadMode,
  uploading,
  checkForReplacement,
  handleAvatarUpload,
  handleDeleteAvatar,
  handleDeleteAvatarGroup,
  selectedAvatarGroup,
  setSelectedAvatarGroup,
  lastUploadedName,
  setLastUploadedName,
  allVoices,
  settings,
  setManagedAvatars
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Image className="w-5 h-5" />
          Avatar Management
        </CardTitle>
        <CardDescription>Upload and manage avatar images (voices are randomly selected)</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Upload Configuration */}
        <div className="space-y-4 p-4 rounded-lg border bg-muted/50">
          <h4 className="font-medium">Upload Configuration</h4>
          
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="avatarName">Avatar Name</Label>
              <Input
                id="avatarName"
                placeholder="Enter avatar name (e.g., 'Happy Cat', 'Serious Dog')"
                value={avatarName}
                onChange={e => {
                  const newName = e.target.value
                  setAvatarName(newName)
                  // Clear the group when name changes in pair mode
                  if (uploadMode === 'pair' && lastUploadedName && newName.trim() !== lastUploadedName) {
                    setSelectedAvatarGroup('')
                  }
                }}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="uploadMode">Upload Mode</Label>
              <select
                id="uploadMode"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={uploadMode}
                onChange={e => {
                  setUploadMode(e.target.value)
                  // Clear group when switching modes
                  setSelectedAvatarGroup('')
                  setLastUploadedName('')
                }}
              >
                <option value="single">Single Image - One image for all states</option>
                <option value="pair">Image Pair - Default and speaking images</option>
              </select>
            </div>
          </div>
        </div>

        {/* Upload Section */}
        {uploadMode === 'single' ? (
          <div className="p-4 rounded-lg border bg-muted/50">
            <label className="flex items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer hover:border-primary transition-colors">
              <input 
                type="file" 
                accept="image/*" 
                onChange={(e) => handleAvatarUpload(e, 'default')}
                className="hidden"
                disabled={uploading || !avatarName.trim()}
              />
              <div className="text-center">
                {uploading ? (
                  <div className="flex items-center gap-2">
                    <div className="animate-spin w-5 h-5 border-2 border-primary border-t-transparent rounded-full"></div>
                    <span className="text-sm">Uploading...</span>
                  </div>
                ) : !avatarName.trim() ? (
                  <>
                    <div className="text-2xl mb-2">⚠️</div>
                    <div className="text-sm font-medium text-yellow-600 dark:text-yellow-400">Enter avatar name first</div>
                    <div className="text-xs text-muted-foreground mt-1">Name is required before uploading</div>
                  </>
                ) : (
                  <>
                    <div className="text-2xl mb-2">📁</div>
                    <div className="text-sm font-medium">Click to upload single avatar image</div>
                    <div className="text-xs text-muted-foreground mt-1">PNG, JPG, GIF up to 5MB</div>
                  </>
                )}
              </div>
            </label>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="p-4 rounded-lg border bg-muted/50">
              <h5 className="text-sm font-medium mb-3">Default Image (Idle State)</h5>
              <label className="flex items-center justify-center w-full h-24 border-2 border-dashed rounded-lg cursor-pointer hover:border-primary transition-colors">
                <input 
                  type="file" 
                  accept="image/*" 
                  onChange={(e) => handleAvatarUpload(e, 'default')}
                  className="hidden"
                  disabled={uploading || !avatarName.trim()}
                />
                <div className="text-center">
                  {uploading ? (
                    <div className="flex items-center gap-2">
                      <div className="animate-spin w-4 h-4 border-2 border-primary border-t-transparent rounded-full"></div>
                      <span className="text-xs">Uploading...</span>
                    </div>
                  ) : !avatarName.trim() ? (
                    <div className="text-xs text-yellow-600 dark:text-yellow-400">Enter name first</div>
                  ) : (
                    <>
                      <div className="text-lg mb-1">😴</div>
                      <div className="text-xs font-medium">Upload default image</div>
                    </>
                  )}
                </div>
              </label>
            </div>
            
            <div className="p-4 rounded-lg border bg-muted/50">
              <h5 className="text-sm font-medium mb-3">Speaking Image (Active State)</h5>
              <label className="flex items-center justify-center w-full h-24 border-2 border-dashed rounded-lg cursor-pointer hover:border-primary transition-colors">
                <input 
                  type="file" 
                  accept="image/*" 
                  onChange={(e) => handleAvatarUpload(e, 'speaking')}
                  className="hidden"
                  disabled={uploading || !avatarName.trim()}
                />
                <div className="text-center">
                  {uploading ? (
                    <div className="flex items-center gap-2">
                      <div className="animate-spin w-4 h-4 border-2 border-primary border-t-transparent rounded-full"></div>
                      <span className="text-xs">Uploading...</span>
                    </div>
                  ) : !avatarName.trim() ? (
                    <div className="text-xs text-yellow-600 dark:text-yellow-400">Enter name first</div>
                  ) : (
                    <>
                      <div className="text-lg mb-1">🗣️</div>
                      <div className="text-xs font-medium">Upload speaking image</div>
                    </>
                  )}
                </div>
              </label>
            </div>
          </div>
        )}

        {/* Uploaded Avatars Grid */}
        {managedAvatars.length > 0 && (
          <div className="space-y-3">
            <h3 className="font-medium">Uploaded Avatars</h3>
            <div className="space-y-4">
              {(() => {
                const grouped = {}
                managedAvatars.forEach(avatar => {
                  const key = avatar.avatar_group_id || `single_${avatar.id}`
                  if (!grouped[key]) grouped[key] = []
                  grouped[key].push(avatar)
                })
                
                return Object.entries(grouped).map(([groupKey, avatars]) => {
                  return (
                    <div key={groupKey} className="p-4 rounded-lg border bg-card">
                      <div className="flex items-center justify-between mb-3">
                        <h4 className="font-medium">{avatars[0].name}</h4>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDeleteAvatarGroup(groupKey, avatars[0].name, avatars.length > 1)}
                        >
                          Delete {avatars.length > 1 ? 'Pair' : 'Avatar'}
                        </Button>
                      </div>
                      
                      <div className="flex gap-3 mb-3">
                        {avatars
                          .sort((a, b) => a.avatar_type === 'default' ? -1 : 1)
                          .map(avatar => (
                            <div key={avatar.id} className="text-center p-3 rounded-lg border bg-muted/50 relative group">
                              {avatars.length > 1 && (
                                <button
                                  onClick={() => handleDeleteAvatar(avatar.id)}
                                  className="absolute -top-1 -right-1 w-5 h-5 bg-destructive hover:bg-destructive/90 text-destructive-foreground rounded-full text-xs opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
                                  title={`Delete ${avatar.avatar_type} image`}
                                >
                                  ×
                                </button>
                              )}
                              
                              <div className="w-16 h-16 rounded-lg overflow-hidden mb-2 mx-auto">
                                <img 
                                  src={`${apiUrl}${avatar.file_path}`}
                                  alt={`${avatar.name} - ${avatar.avatar_type}`}
                                  className="w-full h-full object-cover"
                                  onError={(e) => {
                                    e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><rect width="100" height="100" fill="%23374151"/><text x="50" y="50" text-anchor="middle" dy=".3em" fill="%23d1d5db" font-size="12">Error</text></svg>'
                                  }}
                                />
                              </div>
                              <div className="text-xs font-medium">
                                {avatar.avatar_type === 'default' ? '😴 Default' : '🗣️ Speaking'}
                              </div>
                              <div className="text-xs text-muted-foreground mt-1">
                                {(avatar.file_size / 1024).toFixed(1)}KB
                              </div>
                            </div>
                          ))}
                      </div>
                      

                    </div>
                  )
                })
              })()}
            </div>
          </div>
        )}
        
        {managedAvatars.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            No avatars uploaded yet. Upload some images to get started!
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Due to size limitations, I'll create placeholders for the remaining components
// These would be fully implemented in separate files

function TTSConfiguration({ settings, updateSettings }) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-blue-500">
            <Mic className="w-5 h-5" />
            MonsterTTS Settings
          </CardTitle>
          <CardDescription>AI voices with rate limiting (1 generation every 2 seconds)</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="monstertts-api-key">API Key</Label>
            <Input
              id="monstertts-api-key"
              type="password"
              placeholder="ttsm_12345-abcdef (leave empty to use configured voices only)"
              value={settings.tts?.monstertts?.apiKey || ''}
              onChange={e => updateSettings({ 
                tts: { 
                  ...settings.tts, 
                  monstertts: { 
                    ...settings.tts?.monstertts, 
                    apiKey: e.target.value 
                  } 
                } 
              })}
            />
            <p className="text-sm text-muted-foreground">
              Get your API key at{' '}
              <a href="https://tts.monster/" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                tts.monster
              </a>
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-orange-500">
            <Mic className="w-5 h-5" />
            Google Cloud TTS Settings
          </CardTitle>
          <CardDescription>Google's neural voices. Requires API key and billing account.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="google-api-key">API Key</Label>
            <Input
              id="google-api-key"
              type="password"
              placeholder="AIzaSy... (Google Cloud API Key)"
              value={settings.tts?.google?.apiKey || ''}
              onChange={e => updateSettings({ 
                tts: { 
                  ...settings.tts, 
                  google: { 
                    ...settings.tts?.google, 
                    apiKey: e.target.value 
                  } 
                } 
              })}
            />
            <p className="text-sm text-muted-foreground">
              Create an API key at{' '}
              <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                Google Cloud Console
              </a>
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-purple-500">
            <Mic className="w-5 h-5" />
            Amazon Polly Settings
          </CardTitle>
          <CardDescription>Amazon's neural and standard voices. Requires AWS account.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="polly-access-key">AWS Access Key ID</Label>
            <Input
              id="polly-access-key"
              type="password"
              placeholder="AKIA... (AWS Access Key ID)"
              value={settings.tts?.polly?.accessKey || ''}
              onChange={e => updateSettings({ 
                tts: { 
                  ...settings.tts, 
                  polly: { 
                    ...settings.tts?.polly, 
                    accessKey: e.target.value 
                  } 
                } 
              })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="polly-secret-key">AWS Secret Access Key</Label>
            <Input
              id="polly-secret-key"
              type="password"
              placeholder="Secret Access Key"
              value={settings.tts?.polly?.secretKey || ''}
              onChange={e => updateSettings({ 
                tts: { 
                  ...settings.tts, 
                  polly: { 
                    ...settings.tts?.polly, 
                    secretKey: e.target.value 
                  } 
                } 
              })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="polly-region">AWS Region</Label>
            <Input
              id="polly-region"
              type="text"
              placeholder="us-east-1 (default)"
              value={settings.tts?.polly?.region || ''}
              onChange={e => updateSettings({ 
                tts: { 
                  ...settings.tts, 
                  polly: { 
                    ...settings.tts?.polly, 
                    region: e.target.value 
                  } 
                } 
              })}
            />
            <p className="text-sm text-muted-foreground">
              Create access keys at{' '}
              <a href="https://console.aws.amazon.com/iam/home#/security_credentials" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                AWS IAM Console
              </a>
              {' '}(Polly permissions required)
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// VoiceManager component is now imported from ../components/VoiceManager.jsx

function SpecialEventVoices({ settings, updateSettings, allVoices }) {


  const events = [
    { key: 'raid', name: 'Raids', icon: '⚔️', desc: 'When someone raids your stream' },
    { key: 'bits', name: 'Bits/Cheers', icon: '💎', desc: 'When viewers donate bits' },
    { key: 'sub', name: 'Subscriptions', icon: '⭐', desc: 'New subscribers' },
    { key: 'highlight', name: 'Highlights', icon: '✨', desc: 'Highlighted messages' },
    { key: 'vip', name: 'VIP Messages', icon: '👑', desc: 'Messages from VIPs' }
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-yellow-500" />
          Special Event Voices
        </CardTitle>
        <CardDescription>Assign specific voices to different Twitch events</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {events.map(event => (
            <div key={event.key} className="p-4 rounded-lg border bg-card space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-lg">{event.icon}</span>
                <div>
                  <div className="font-medium text-sm">{event.name}</div>
                  <div className="text-xs text-muted-foreground">{event.desc}</div>
                </div>
              </div>
              <select 
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={settings.specialVoices?.[event.key]?.voiceId || ''}
                onChange={e => updateSettings({
                  specialVoices: { ...settings.specialVoices, [event.key]: { voiceId: e.target.value } }
                })}>
                <option value="">🎲 Random Voice</option>
                {allVoices.filter(v => v.enabled).map(v => <option key={v.id} value={v.id}>{v.name} ({v.provider})</option>)}
              </select>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function MessageFiltering({ settings, updateSettings, apiUrl }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquare className="w-5 h-5" />
          Message Filtering
        </CardTitle>
        <CardDescription>Control which messages get processed for TTS</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
          <div className="space-y-1">
            <Label htmlFor="filtering-enabled" className="text-base">Enable Message Filtering</Label>
            <p className="text-sm text-muted-foreground">Filter messages before TTS processing</p>
          </div>
          <Switch
            id="filtering-enabled"
            checked={settings.messageFiltering?.enabled ?? true}
            onCheckedChange={checked => updateSettings({ 
              messageFiltering: { 
                ...settings.messageFiltering, 
                enabled: checked 
              } 
            })}
          />
        </div>

        {(settings.messageFiltering?.enabled !== false) && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="minLength">Minimum Length</Label>
                <Input
                  id="minLength"
                  type="number"
                  min="1"
                  max="100"
                  value={settings.messageFiltering?.minLength ?? 1}
                  onChange={e => updateSettings({ 
                    messageFiltering: { 
                      ...settings.messageFiltering, 
                      minLength: parseInt(e.target.value) || 1 
                    } 
                  })}
                />
                <p className="text-xs text-muted-foreground">Messages shorter than this will be skipped</p>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="maxLength">Maximum Length</Label>
                <Input
                  id="maxLength"
                  type="number"
                  min="10"
                  max="2000"
                  value={settings.messageFiltering?.maxLength ?? 500}
                  onChange={e => updateSettings({ 
                    messageFiltering: { 
                      ...settings.messageFiltering, 
                      maxLength: parseInt(e.target.value) || 500 
                    } 
                  })}
                />
                <p className="text-xs text-muted-foreground">Messages longer than this will be truncated</p>
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="skipCommands"
                  checked={settings.messageFiltering?.skipCommands ?? true}
                  onCheckedChange={checked => updateSettings({ 
                    messageFiltering: { 
                      ...settings.messageFiltering, 
                      skipCommands: checked 
                    } 
                  })}
                />
                <Label htmlFor="skipCommands" className="text-sm font-normal">
                  Skip Commands - Messages starting with ! or / (bot commands)
                </Label>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="skipEmotes"
                  checked={settings.messageFiltering?.skipEmotes ?? false}
                  onCheckedChange={checked => updateSettings({ 
                    messageFiltering: { 
                      ...settings.messageFiltering, 
                      skipEmotes: checked 
                    } 
                  })}
                />
                <Label htmlFor="skipEmotes" className="text-sm font-normal">
                  Skip Emote-Only Messages (experimental)
                </Label>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="removeUrls"
                  checked={settings.messageFiltering?.removeUrls ?? true}
                  onCheckedChange={checked => updateSettings({ 
                    messageFiltering: { 
                      ...settings.messageFiltering, 
                      removeUrls: checked 
                    } 
                  })}
                />
                <Label htmlFor="removeUrls" className="text-sm font-normal">
                  Remove URLs from messages before TTS processing
                </Label>
              </div>

              <div className="flex items-center space-x-2">
                <Checkbox
                  id="ignoreIfUserSpeaking"
                  checked={settings.messageFiltering?.ignoreIfUserSpeaking ?? true}
                  onCheckedChange={checked => updateSettings({ 
                    messageFiltering: { 
                      ...settings.messageFiltering, 
                      ignoreIfUserSpeaking: checked 
                    } 
                  })}
                />
                <div className="space-y-1">
                  <Label htmlFor="ignoreIfUserSpeaking" className="text-sm font-normal">
                    Ignore new messages from a user who is already speaking
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    When enabled, if a user sends a new message while their previous message is still playing, 
                    the new message will be ignored.
                  </p>
                </div>
              </div>
            </div>

            <Separator />

            <div className="space-y-4">
              <h4 className="font-medium flex items-center gap-2">
                <span>🤬</span>
                Profanity Filter
              </h4>
              
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="profanityFilterEnabled"
                  checked={settings.messageFiltering?.profanityFilter?.enabled ?? false}
                  onCheckedChange={checked => updateSettings({ 
                    messageFiltering: { 
                      ...settings.messageFiltering, 
                      profanityFilter: {
                        ...settings.messageFiltering?.profanityFilter,
                        enabled: checked
                      }
                    } 
                  })}
                />
                <Label htmlFor="profanityFilterEnabled" className="text-sm font-normal">
                  Enable Profanity Filter
                </Label>
              </div>

              {settings.messageFiltering?.profanityFilter?.enabled && (
                <div className="space-y-4 pl-6 border-l-2">
                  <div className="space-y-2">
                    <Label htmlFor="replacementText">Replacement Text</Label>
                    <Input
                      id="replacementText"
                      value={settings.messageFiltering?.profanityFilter?.replacement ?? 'beep'}
                      onChange={e => updateSettings({ 
                        messageFiltering: { 
                          ...settings.messageFiltering, 
                          profanityFilter: {
                            ...settings.messageFiltering?.profanityFilter,
                            replacement: e.target.value
                          }
                        } 
                      })}
                      placeholder="beep"
                    />
                    <p className="text-xs text-muted-foreground">Text to replace filtered words with</p>
                  </div>

                  <div className="space-y-2">
                    <Label>Custom Words to Filter</Label>
                    <ProfanityWordsManager 
                      words={settings.messageFiltering?.profanityFilter?.customWords || []}
                      onUpdate={(words) => updateSettings({ 
                        messageFiltering: { 
                          ...settings.messageFiltering, 
                          profanityFilter: {
                            ...settings.messageFiltering?.profanityFilter,
                            customWords: words
                          }
                        } 
                      })}
                    />
                  </div>
                </div>
              )}
            </div>

            <Separator />

            <div className="space-y-3">
              <h4 className="font-medium">Ignored Users</h4>
              <IgnoredUsersManager 
                ignoredUsers={settings.messageFiltering?.ignoredUsers || []}
                onUpdate={(users) => updateSettings({ 
                  messageFiltering: { 
                    ...settings.messageFiltering, 
                    ignoredUsers: users 
                  } 
                })}
              />
            </div>

            <div className="p-4 rounded-lg border bg-muted/50">
              <h4 className="font-medium mb-2 flex items-center gap-2">
                <TestTube2 className="w-4 h-4" />
                Test Message Filter
              </h4>
              <MessageFilterTester apiUrl={apiUrl} />
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function Simulator({ onSend }) {
  const [user, setUser] = useState('TestUser')
  const [text, setText] = useState('Hello Chat Yappers!')
  const [eventType, setEventType] = useState('chat')
  const [userMode, setUserMode] = useState('single') // 'single' or 'random'
  const [burstCount, setBurstCount] = useState(5)
  const [burstDelay, setBurstDelay] = useState(1000)
  const [isSendingBurst, setIsSendingBurst] = useState(false)
  
  const eventTypes = [
    { value: 'chat', label: '💬 Chat', desc: 'Regular chat message' },
    { value: 'raid', label: '⚔️ Raid', desc: 'Raid event' },
    { value: 'bits', label: '💎 Bits', desc: 'Bits/Cheers' },
    { value: 'sub', label: '⭐ Subscribe', desc: 'New subscription' },
    { value: 'highlight', label: '✨ Highlight', desc: 'Highlighted message' },
    { value: 'vip', label: '👑 VIP', desc: 'VIP message' }
  ]

  const randomUsernames = [
    'StreamFan2024', 'GamerGirl99', 'NightOwl_', 'CoffeeAddict', 'PixelMaster',
    'ChatLurker', 'MemeLord420', 'RetroGamer', 'TechNinja', 'BookwormReads',
    'MusicLover88', 'ArtisticSoul', 'CodeWarrior', 'NatureLover', 'FitnessFreak'
  ]

  const testMessages = [
    'Hello everyone!', 'Nice stream!', 'Wow that was amazing!', 'Keep it up!', 
    'Love this content!', 'Great gameplay!', 'This is so good!', 'More please!',
    'You are awesome!', 'Best streamer ever!', 'Can\'t stop watching!', 'So entertaining!'
  ]

  const getRandomUsername = () => {
    return randomUsernames[Math.floor(Math.random() * randomUsernames.length)] + Math.floor(Math.random() * 999)
  }

  const getRandomMessage = () => {
    return testMessages[Math.floor(Math.random() * testMessages.length)]
  }

  const sendBurstMessages = async () => {
    setIsSendingBurst(true)
    
    for (let i = 0; i < burstCount; i++) {
      const messageUser = userMode === 'single' ? user : getRandomUsername()
      const messageText = userMode === 'single' ? text : getRandomMessage()
      
      await onSend(messageUser, messageText, eventType)
      
      // Add delay between messages (except for the last one)
      if (i < burstCount - 1) {
        await new Promise(resolve => setTimeout(resolve, burstDelay))
      }
    }
    
    setIsSendingBurst(false)
  }
  
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TestTube2 className="w-5 h-5" />
          Test Simulator
        </CardTitle>
        <CardDescription>Test your TTS configuration with single or multiple users</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* User Mode Selection */}
        <div className="space-y-3">
          <Label className="text-base font-medium">User Mode</Label>
          <div className="flex gap-4">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="radio"
                name="userMode"
                value="single"
                checked={userMode === 'single'}
                onChange={e => setUserMode(e.target.value)}
                className="w-4 h-4"
              />
              <span className="text-sm">🎯 Single User - Test per-user queuing</span>
            </label>
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="radio"
                name="userMode"
                value="random"
                checked={userMode === 'random'}
                onChange={e => setUserMode(e.target.value)}
                className="w-4 h-4"
              />
              <span className="text-sm">🎲 Random Users - Test parallel audio</span>
            </label>
          </div>
          <p className="text-xs text-muted-foreground">
            {userMode === 'single' 
              ? "All messages will be from the same user - perfect for testing that same user won't interrupt themselves"
              : "Each message will be from different random users - perfect for testing multiple concurrent voices"
            }
          </p>
        </div>

        <Separator />

        {/* Single Message Section */}
        <div className="space-y-4">
          <Label className="text-base font-medium">Single Message Test</Label>
          
          <div className="grid md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="sim-user">Username</Label>
              <Input
                id="sim-user"
                placeholder="TestUser"
                value={user} 
                onChange={e => setUser(e.target.value)}
                disabled={userMode === 'random'}
              />
              {userMode === 'random' && (
                <p className="text-xs text-muted-foreground">Auto-generated in random mode</p>
              )}
            </div>
            
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="sim-text">Message</Label>
              <Input
                id="sim-text"
                placeholder="Type your test message here..."
                value={text} 
                onChange={e => setText(e.target.value)}
                disabled={userMode === 'random'}
              />
              {userMode === 'random' && (
                <p className="text-xs text-muted-foreground">Auto-generated in random mode</p>
              )}
            </div>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="sim-event">Event Type</Label>
            <select 
              id="sim-event"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              value={eventType} 
              onChange={e => setEventType(e.target.value)}
            >
              {eventTypes.map(type => 
                <option key={type.value} value={type.value}>{type.label} - {type.desc}</option>
              )}
            </select>
          </div>
          
          <div className="flex justify-center pt-2">
            <Button 
              size="lg"
              className="gap-2" 
              onClick={() => onSend(
                userMode === 'single' ? user : getRandomUsername(),
                userMode === 'single' ? text : getRandomMessage(),
                eventType
              )}
            >
              <span className="text-lg">🚀</span>
              Send Test Message
            </Button>
          </div>
        </div>

        <Separator />

        {/* Burst Messages Section */}
        <div className="space-y-4">
          <Label className="text-base font-medium">Burst Message Testing</Label>
          <p className="text-sm text-muted-foreground">
            Send multiple messages rapidly to test {userMode === 'single' ? 'per-user queuing behavior' : 'parallel audio handling'}
          </p>
          
          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="burst-count">Number of Messages</Label>
              <Input
                id="burst-count"
                type="number"
                min="2"
                max="20"
                value={burstCount}
                onChange={e => setBurstCount(parseInt(e.target.value) || 5)}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="burst-delay">Delay Between Messages (ms)</Label>
              <Input
                id="burst-delay"
                type="number"
                min="100"
                max="5000"
                step="100"
                value={burstDelay}
                onChange={e => setBurstDelay(parseInt(e.target.value) || 1000)}
              />
            </div>
          </div>
          
          <div className="flex justify-center pt-2">
            <Button 
              size="lg"
              className="gap-2" 
              onClick={sendBurstMessages}
              disabled={isSendingBurst}
            >
              {isSendingBurst ? (
                <>
                  <span className="text-lg">⏳</span>
                  Sending Burst...
                </>
              ) : (
                <>
                  <span className="text-lg">💥</span>
                  Send {burstCount} Messages
                </>
              )}
            </Button>
          </div>
          
          {userMode === 'single' && (
            <div className="bg-blue-50 dark:bg-blue-950 p-3 rounded-lg">
              <p className="text-sm text-blue-700 dark:text-blue-300">
                <strong>Single User Mode:</strong> Watch how the system handles rapid messages from "{user}" - 
                new messages should be ignored while previous ones are still speaking.
              </p>
            </div>
          )}
          
          {userMode === 'random' && (
            <div className="bg-green-50 dark:bg-green-950 p-3 rounded-lg">
              <p className="text-sm text-green-700 dark:text-green-300">
                <strong>Random User Mode:</strong> Watch how the system handles multiple users speaking simultaneously - 
                different users should be able to speak in parallel.
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function MessageFilterTester({ apiUrl }) {
  const [testMessage, setTestMessage] = useState('')
  const [testUsername, setTestUsername] = useState('')
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(false)

  const testFilter = async () => {
    if (!testMessage.trim()) return
    
    setTesting(true)
    try {
      const response = await fetch(`${apiUrl}/api/message-filter/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          message: testMessage,
          username: testUsername 
        })
      })
      const result = await response.json()
      setTestResult(result)
    } catch (error) {
      setTestResult({ success: false, error: error.message })
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        <Input
          placeholder="Username (optional)"
          value={testUsername}
          onChange={e => setTestUsername(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && testFilter()}
        />
        <Input
          placeholder="Enter a test message..."
          className="md:col-span-2"
          value={testMessage}
          onChange={e => setTestMessage(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && testFilter()}
        />
      </div>
      <Button
        onClick={testFilter}
        disabled={testing || !testMessage.trim()}
        className="w-full"
      >
        {testing ? 'Testing...' : 'Test Message Filter'}
      </Button>
      
      {testResult && (
        <div className={`p-3 rounded-lg border text-sm ${
          testResult.success 
            ? testResult.should_process 
              ? 'bg-green-500/10 border-green-500/50' 
              : 'bg-yellow-500/10 border-yellow-500/50'
            : 'bg-destructive/10 border-destructive/50'
        }`}>
          {testResult.success ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2 font-medium">
                {testResult.should_process ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                {testResult.should_process ? 'Message will be processed' : 'Message will be filtered out'}
              </div>
              
              {testResult.was_modified && (
                <div className="space-y-1 text-xs">
                  <p>Original: "{testResult.original_message}"</p>
                  <p>Filtered: "{testResult.filtered_message}"</p>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <XCircle className="w-4 h-4" />
              Error: {testResult.error}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function IgnoredUsersManager({ ignoredUsers, onUpdate }) {
  const [newUser, setNewUser] = useState('')

  const addUser = () => {
    const username = newUser.trim()
    if (!username) return
    
    if (ignoredUsers.some(user => user.toLowerCase() === username.toLowerCase())) {
      alert('User is already in the ignored list')
      return
    }
    
    onUpdate([...ignoredUsers, username])
    setNewUser('')
  }

  const removeUser = (userToRemove) => {
    onUpdate(ignoredUsers.filter(user => user !== userToRemove))
  }

  const clearAllUsers = () => {
    if (ignoredUsers.length === 0) return
    if (confirm(`Are you sure you want to remove all ${ignoredUsers.length} ignored users?`)) {
      onUpdate([])
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <Input
          placeholder="Enter username to ignore..."
          value={newUser}
          onChange={e => setNewUser(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && addUser()}
        />
        <Button
          onClick={addUser}
          disabled={!newUser.trim()}
        >
          Add
        </Button>
      </div>

      {ignoredUsers.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium">
              Ignored Users ({ignoredUsers.length})
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllUsers}
              className="h-auto py-1 px-2 text-xs text-destructive hover:text-destructive"
            >
              Clear All
            </Button>
          </div>
          
          <div className="max-h-32 overflow-y-auto space-y-1">
            {ignoredUsers.map((user, index) => (
              <div key={index} className="flex items-center justify-between p-2 rounded-lg border bg-card">
                <span className="text-sm font-mono">{user}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeUser(user)}
                  className="h-auto py-1 px-2 text-destructive hover:text-destructive"
                  title={`Remove ${user}`}
                >
                  ✕
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {ignoredUsers.length === 0 && (
        <p className="text-xs text-muted-foreground text-center py-2">
          No users ignored yet
        </p>
      )}
    </div>
  )
}

function ProfanityWordsManager({ words, onUpdate }) {
  const [newWord, setNewWord] = useState('')

  const addWord = () => {
    const word = newWord.trim().toLowerCase()
    if (!word) return
    
    if (words.some(w => w.toLowerCase() === word)) {
      alert('This word is already in the filter list')
      return
    }
    
    onUpdate([...words, word])
    setNewWord('')
  }

  const removeWord = (wordToRemove) => {
    onUpdate(words.filter(w => w !== wordToRemove))
  }

  const clearAllWords = () => {
    if (words.length === 0) return
    if (confirm(`Are you sure you want to remove all ${words.length} filtered words?`)) {
      onUpdate([])
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <Input
          placeholder="Enter word to filter..."
          value={newWord}
          onChange={e => setNewWord(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && addWord()}
        />
        <Button
          onClick={addWord}
          disabled={!newWord.trim()}
        >
          Add
        </Button>
      </div>

      {words.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium">
              Filtered Words ({words.length})
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllWords}
              className="h-auto py-1 px-2 text-xs text-destructive hover:text-destructive"
            >
              Clear All
            </Button>
          </div>

          <div className="flex flex-wrap gap-2">
            {words.map((word, index) => (
              <div 
                key={index}
                className="flex items-center gap-1 px-2 py-1 bg-muted rounded text-xs"
              >
                <span>{word}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeWord(word)}
                  className="h-auto py-0 px-1 text-destructive hover:text-destructive"
                  title={`Remove ${word}`}
                >
                  ✕
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {words.length === 0 && (
        <p className="text-xs text-muted-foreground text-center py-2">
          No words filtered yet. Add words to block from messages.
        </p>
      )}
    </div>
  )
}
