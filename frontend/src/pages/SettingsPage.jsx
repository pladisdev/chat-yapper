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
import GeneralSettings from '../components/settings/GeneralSettings'
import AvatarManagement from '../components/settings/AvatarManagement'
import TTSConfiguration from '../components/settings/TTSConfiguration'
import TwitchIntegrationTab from '../components/settings/TwitchIntegration'
import MessageFiltering from '../components/settings/MessageFiltering'
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
              setUploading={setUploading}
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
            <TwitchIntegrationTab settings={settings} updateSettings={updateSettings} allVoices={allVoices} />
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
            <h3 className="font-medium text-lg">🎥 OBS Studio Integration</h3>
            <div className="p-4 rounded-lg border bg-card">
              <div className="space-y-3">
                <p className="text-sm font-medium">Use Chat Yapper with OBS Studio</p>
                <p className="text-sm text-muted-foreground">
                  Display animated chat avatars in your stream by adding the yappers page as a Browser Source in OBS.
                </p>
                <div className="space-y-3">
                  <div>
                    <p className="text-xs font-medium mb-2">📋 Steps to add to OBS:</p>
                    <ol className="list-decimal list-inside text-xs text-muted-foreground space-y-1 ml-2">
                      <li>In OBS, right-click in Sources and select "Add" → "Browser"</li>
                      <li>Create new source and name it how you like</li>
                      <li>Set the URL to: <code className="bg-muted px-1 rounded text-xs">http://localhost:8000/yappers</code></li>
                      <li>Recommend Width: 1000 and Recommend Height: 600</li>
                      <li>Check "Control audio via OBS", "Shutdown source when not visible" and "Refresh browser when scene becomes active"</li>
                      <li>Click OK - avatars will appear when chat messages are spoken</li>
                    </ol>
                  </div>
                </div>
              </div>
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
