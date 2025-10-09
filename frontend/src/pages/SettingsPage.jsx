import React, { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import logger from '../utils/logger'
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
        logger.info('🔇 TTS globally stopped via WebSocket')
        setSettings(prevSettings => ({
          ...prevSettings,
          ttsControl: { enabled: false }
        }))
      } else if (data.type === 'tts_global_resumed') {
        logger.info('🔊 TTS globally resumed via WebSocket')
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
    logger.info('🧪 Sending test message:', { user, text, eventType })
    const fd = new FormData()
    fd.set('user', user)
    fd.set('text', text)
    fd.set('eventType', eventType)
    
    try {
      const response = await fetch(`${apiUrl}/api/simulate`, { method: 'POST', body: fd })
      const result = await response.json()
      logger.info('✅ Simulate response:', result)
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

  const handleToggleAvatarDisabled = async (avatarId) => {
    try {
      const response = await fetch(`${apiUrl}/api/avatars/${avatarId}/toggle-disabled`, {
        method: 'PUT'
      })
      
      const result = await response.json()
      if (result.success) {
        const avatarsResponse = await fetch(`${apiUrl}/api/avatars/managed`)
        const avatarsData = await avatarsResponse.json()
        setManagedAvatars(avatarsData?.avatars || [])
      } else {
        alert(`Toggle failed: ${result.error}`)
      }
    } catch (error) {
      alert(`Toggle error: ${error.message}`)
    }
  }

  const handleToggleAvatarGroupDisabled = async (groupId, avatarName, isPair) => {
    try {
      const response = await fetch(`${apiUrl}/api/avatars/group/${encodeURIComponent(groupId)}/toggle-disabled`, {
        method: 'PUT'
      })
      
      const result = await response.json()
      if (result.success) {
        const avatarsResponse = await fetch(`${apiUrl}/api/avatars/managed`)
        const avatarsData = await avatarsResponse.json()
        setManagedAvatars(avatarsData?.avatars || [])
      } else {
        alert(`Toggle failed: ${result.error}`)
      }
    } catch (error) {
      alert(`Toggle error: ${error.message}`)
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
          <TabsList className="grid w-full grid-cols-7 lg:w-auto lg:inline-grid">
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
            <TabsTrigger value="about" className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              <span className="hidden sm:inline">About</span>
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
              handleToggleAvatarDisabled={handleToggleAvatarDisabled}
              handleToggleAvatarGroupDisabled={handleToggleAvatarGroupDisabled}
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
            {/* <SpecialEventVoices settings={settings} updateSettings={updateSettings} allVoices={allVoices} /> */}
          </TabsContent>

          <TabsContent value="filtering" className="space-y-6">
            <MessageFiltering settings={settings} updateSettings={updateSettings} apiUrl={apiUrl} />
          </TabsContent>

          <TabsContent value="test" className="space-y-6">
            <Simulator onSend={simulate} />
          </TabsContent>

          <TabsContent value="about" className="space-y-6">
            <AboutSection />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

// Sub-components would be imported from separate files in a real app
// For now, including them inline for completeness

function TwitchIntegration({ settings, updateSettings }) {
  const [twitchStatus, setTwitchStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [channelInput, setChannelInput] = useState('');

  // Check Twitch connection status on component mount
  useEffect(() => {
    checkTwitchStatus();
  }, []);

  // Sync channel input with settings
  useEffect(() => {
    if (settings.twitch?.channel !== undefined) {
      setChannelInput(settings.twitch.channel || '');
    }
  }, [settings.twitch?.channel]);

  const checkTwitchStatus = async () => {
    try {
      const response = await fetch('/api/twitch/status');
      const status = await response.json();
      setTwitchStatus(status);
    } catch (error) {
      logger.error('Failed to check Twitch status:', error);
      setTwitchStatus({ connected: false });
    }
  };

  const connectToTwitch = () => {
    // Open OAuth flow in same window
    window.location.href = '/auth/twitch';
  };

  // Check for error parameter in URL
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const error = urlParams.get('error');
    
    if (error === 'twitch_not_configured') {
      alert('⚠️ Twitch integration not configured!\n\nThe developer needs to set up Twitch OAuth credentials.\nSee TWITCH_SETUP.md for instructions.');
      // Clear error from URL
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const disconnectTwitch = async () => {
    if (!confirm('Are you sure you want to disconnect from Twitch?')) return;
    
    setLoading(true);
    try {
      const response = await fetch('/api/twitch/disconnect', { method: 'DELETE' });
      const result = await response.json();
      
      if (result.success) {
        setTwitchStatus({ connected: false });
        // Clear Twitch settings
        updateSettings({ 
          twitch: { 
            ...settings.twitch, 
            enabled: false 
          } 
        });
        logger.info('Successfully disconnected from Twitch');
      } else {
        alert('Failed to disconnect: ' + result.error);
      }
    } catch (error) {
      logger.error('Error disconnecting from Twitch:', error);
      alert('Network error while disconnecting');
    } finally {
      setLoading(false);
    }
  };

  const updateChannel = () => {
    updateSettings({ 
      twitch: { 
        ...settings.twitch, 
        channel: channelInput.trim() 
      } 
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Zap className="w-5 h-5 text-purple-500" />
          Twitch Integration
        </CardTitle>
        <CardDescription>
          Connect to your Twitch account to enable chat TTS
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {!twitchStatus?.connected ? (
          <div className="text-center space-y-4 py-8">
            <div className="space-y-2">
              <h3 className="text-lg font-medium">Connect to Twitch</h3>
              <p className="text-sm text-muted-foreground max-w-md mx-auto">
                Authorize Chat Yapper to read your Twitch chat. This is secure and you can 
                revoke access at any time in your Twitch settings.
              </p>
            </div>
            
            <Button 
              onClick={connectToTwitch} 
              size="lg"
              className="bg-purple-600 hover:bg-purple-700"
              disabled={loading}
            >
              <Zap className="w-4 h-4 mr-2" />
              {loading ? 'Connecting...' : 'Connect to Twitch'}
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Connected Status */}
            <div className="flex items-center justify-between p-4 rounded-lg border bg-emerald-800 text-white">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <div>
                  <p className="font-medium">Connected to Twitch</p>
                  <p className="text-sm text-emerald-100">
                    Logged in as: {twitchStatus.display_name} (@{twitchStatus.username})
                  </p>
                </div>
              </div>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={disconnectTwitch}
                disabled={loading}
                className="border-red-500 text-red-400 hover:bg-red-600 hover:text-white"
              >
                {loading ? 'Disconnecting...' : 'Disconnect'}
              </Button>
            </div>

            {/* Enable/Disable Toggle */}
            <div className="flex items-center justify-between p-4 rounded-lg border bg-card">
              <div className="space-y-1">
                <Label htmlFor="twitch-enabled" className="text-base">Enable Chat TTS</Label>
                <p className="text-sm text-muted-foreground">
                  Start reading chat messages from your Twitch channel
                </p>
              </div>
              <Switch
                id="twitch-enabled"
                checked={!!settings.twitch?.enabled}
                onCheckedChange={checked => updateSettings({ 
                  twitch: { 
                    ...settings.twitch, 
                    enabled: checked,
                    // Set the connected username as the channel by default
                    channel: checked && !settings.twitch?.channel ? twitchStatus.username : settings.twitch?.channel
                  } 
                })}
              />
            </div>

            {/* Channel Selection */}
            {settings.twitch?.enabled && (
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="channel">Channel to Monitor</Label>
                  <div className="flex gap-2">
                    <Input
                      id="channel"
                      placeholder="Enter channel name (without #)"
                      value={channelInput}
                      onChange={e => setChannelInput(e.target.value)}
                      onKeyPress={e => e.key === 'Enter' && updateChannel()}
                      className="flex-1"
                    />
                    <Button
                      onClick={updateChannel}
                      disabled={channelInput.trim() === (settings.twitch?.channel || '')}
                      size="sm"
                    >
                      Update
                    </Button>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Usually your own channel: <code>{twitchStatus.username}</code>
                  </p>
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

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

// The new OAuth-based TwitchIntegration component is defined above
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
  handleToggleAvatarDisabled,
  handleToggleAvatarGroupDisabled,
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
                    <div key={groupKey} className={`p-4 rounded-lg border ${avatars.some(avatar => avatar.disabled) ? 'bg-muted/30 opacity-60' : 'bg-card'}`}>
                      <div className="flex items-center justify-between mb-3">
                        <h4 className={`font-medium flex items-center gap-2 ${avatars.some(avatar => avatar.disabled) ? 'text-muted-foreground' : ''}`}>
                          {avatars[0].name}
                          {avatars.some(avatar => avatar.disabled) && (
                            <span className="text-xs bg-muted px-2 py-1 rounded-full text-muted-foreground">
                              DISABLED
                            </span>
                          )}
                        </h4>
                        <div className="flex gap-2">
                          <Button
                            variant={avatars.some(avatar => avatar.disabled) ? "default" : "outline"}
                            size="sm"
                            onClick={() => handleToggleAvatarGroupDisabled(groupKey, avatars[0].name, avatars.length > 1)}
                          >
                            {avatars.some(avatar => avatar.disabled) ? 'Enable' : 'Disable'}
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => handleDeleteAvatarGroup(groupKey, avatars[0].name, avatars.length > 1)}
                          >
                            Delete {avatars.length > 1 ? 'Pair' : 'Avatar'}
                          </Button>
                        </div>
                      </div>
                      
                      <div className="flex gap-3 mb-3">
                        {avatars
                          .sort((a, b) => a.avatar_type === 'default' ? -1 : 1)
                          .map(avatar => (
                            <div key={avatar.id} className={`text-center p-3 rounded-lg border ${avatar.disabled ? 'bg-muted/30 opacity-50' : 'bg-muted/50'} relative group`}>
                              {avatars.length > 1 && (
                                <>
                                  <button
                                    onClick={() => handleToggleAvatarDisabled(avatar.id)}
                                    className={`absolute -top-1 -left-1 w-5 h-5 ${avatar.disabled ? 'bg-green-600 hover:bg-green-700' : 'bg-amber-600 hover:bg-amber-700'} text-white rounded-full text-xs opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center`}
                                    title={`${avatar.disabled ? 'Enable' : 'Disable'} ${avatar.avatar_type} image`}
                                  >
                                    {avatar.disabled ? '✓' : '⏸'}
                                  </button>
                                  <button
                                    onClick={() => handleDeleteAvatar(avatar.id)}
                                    className="absolute -top-1 -right-1 w-5 h-5 bg-destructive hover:bg-destructive/90 text-destructive-foreground rounded-full text-xs opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
                                    title={`Delete ${avatar.avatar_type} image`}
                                  >
                                    ×
                                  </button>
                                </>
                              )}
                              
                              <div className="w-16 h-16 rounded-lg overflow-hidden mb-2 mx-auto relative">
                                <img 
                                  src={`${apiUrl}${avatar.file_path}`}
                                  alt={`${avatar.name} - ${avatar.avatar_type}`}
                                  className={`w-full h-full object-cover ${avatar.disabled ? 'grayscale' : ''}`}
                                  onError={(e) => {
                                    e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><rect width="100" height="100" fill="%23374151"/><text x="50" y="50" text-anchor="middle" dy=".3em" fill="%23d1d5db" font-size="12">Error</text></svg>'
                                  }}
                                />
                                {avatar.disabled && (
                                  <div className="absolute inset-0 bg-black/20 flex items-center justify-center">
                                    <span className="text-white text-xs font-bold">DISABLED</span>
                                  </div>
                                )}
                              </div>
                              <div className={`text-xs font-medium ${avatar.disabled ? 'text-muted-foreground' : ''}`}>
                                {avatar.avatar_type === 'default' ? '😴 Default' : '🗣️ Speaking'}
                                {avatar.disabled && ' (Disabled)'}
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


            </div>

            <Separator />

            <div className="space-y-6">
              <h4 className="font-medium flex items-center gap-2 text-lg">
                <span>⏱️</span>
                Rate Limiting & Message Control
              </h4>
              
              <div className="space-y-4">
                <div className="space-y-4">
                  <div className="flex items-center space-x-2 mb-3">
                    <Checkbox
                      id="enableSpamFilter"
                      checked={settings.messageFiltering?.enableSpamFilter ?? true}
                      onCheckedChange={checked => updateSettings({ 
                        messageFiltering: { 
                          ...settings.messageFiltering, 
                          enableSpamFilter: checked 
                        } 
                      })}
                    />
                    <div className="space-y-1 flex-1">
                      <Label htmlFor="enableSpamFilter" className="text-base font-medium">
                        🚫 Rate Limit Users
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        Prevent users from sending too many messages in a short time period. New messages from rate-limited users are completely ignored.
                      </p>
                    </div>
                  </div>

                  {settings.messageFiltering?.enableSpamFilter !== false && (
                    <div className="ml-6 space-y-3">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="spamThreshold">Max Messages</Label>
                          <Input
                            id="spamThreshold"
                            type="number"
                            min="2"
                            max="20"
                            value={settings.messageFiltering?.spamThreshold ?? 5}
                            onChange={e => updateSettings({ 
                              messageFiltering: { 
                                ...settings.messageFiltering, 
                                spamThreshold: parseInt(e.target.value) || 5 
                              } 
                            })}
                          />
                          <p className="text-xs text-muted-foreground">Maximum messages allowed</p>
                        </div>

                        <div className="space-y-2">
                          <Label htmlFor="spamTimeWindow">Time Window (seconds)</Label>
                          <Input
                            id="spamTimeWindow"
                            type="number"
                            min="5"
                            max="60"
                            value={settings.messageFiltering?.spamTimeWindow ?? 10}
                            onChange={e => updateSettings({ 
                              messageFiltering: { 
                                ...settings.messageFiltering, 
                                spamTimeWindow: parseInt(e.target.value) || 10 
                              } 
                            })}
                          />
                          <p className="text-xs text-muted-foreground">Within this many seconds</p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                <div>
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
                      <Label htmlFor="ignoreIfUserSpeaking" className="text-base font-medium">
                        🔊 Ignore New Messages from Speaking User
                      </Label>
                      <p className="text-sm text-muted-foreground">
                        When a user's message is currently playing TTS, ignore any new messages from that same user until the current message finishes. This prevents interrupting or queueing multiple messages from one person.
                      </p>
                    </div>
                  </div>
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

function AboutSection() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5" />
          About Chat Yapper
        </CardTitle>
        <CardDescription>Information and support for Chat Yapper TTS System</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="space-y-4">
          <div className="p-4 rounded-lg border bg-muted/50">
            <h3 className="font-medium text-lg mb-2">Chat Yapper</h3>
            <p className="text-sm text-muted-foreground mb-4">
              A way to have your chat talk through avatars! At the same time... not obnoxious at all...
            </p>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="font-medium">✨ Features:</span>
              </div>
              <ul className="list-disc list-inside ml-4 space-y-1 text-muted-foreground">
                <li>Voice avatars supporting multi-image avatars</li>
                <li>Multiple TTS providers (Edge, MonsterTTS, Google Cloud, Amazon Polly)</li>
                <li>Message filtering and rate limiting</li>
                <li>Twitch integration</li>
              </ul>
            </div>
          </div>

          <Separator />

          <div className="space-y-4">
            <h3 className="font-medium text-lg">Support & Contact</h3>
            <div className="p-4 rounded-lg border bg-card">
              <div className="flex items-center gap-3">
                <div className="text-2xl"></div>
                <div>
                  <p className="font-medium">Need help or have questions?</p>
                  <p className="text-sm text-muted-foreground">
                    Contact the developer for support, bug reports, or feature requests
                  </p>
                  <a 
                    href="mailto:pladisdev@gmail.com" 
                    className="text-primary hover:underline font-mono text-sm"
                  >
                    pladisdev@gmail.com
                  </a>
                </div>
              </div>
            </div>
          </div>

          <Separator />

          <div className="space-y-4">
            <h3 className="font-medium text-lg">ℹ️ System Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-3 rounded-lg border bg-card">
                <div className="text-sm font-medium mb-1">Version</div>
                <div className="text-xs text-muted-foreground">Chat Yapper v1.0.0</div>
              </div>
              <div className="p-3 rounded-lg border bg-card">
                <div className="text-sm font-medium mb-1">Status</div>
                <div className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" />
                  System Running
                </div>
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
