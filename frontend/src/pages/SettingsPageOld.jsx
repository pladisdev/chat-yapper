import React, { useEffect, useState } from 'react'

export default function SettingsPage() {
  const [settings, setSettings] = useState(null)
  const [log, setLog] = useState([])
  const [allVoices, setAllVoices] = useState([])

  // Determine the correct API URL
  const apiUrl = location.hostname === 'localhost' && (location.port === '5173' || location.port === '5174')
    ? 'http://localhost:8000'  // Vite dev server connecting to backend
    : '' // Production or direct backend access (relative URLs)

  useEffect(() => {
    // Load settings
    fetch(`${apiUrl}/api/settings`).then(r => r.json()).then(data => {
      setSettings(data)
    })
    
    // Load voices from database
    fetch(`${apiUrl}/api/voices`).then(r => r.json()).then(data => {
      setAllVoices(data?.voices || [])
    })
  }, [apiUrl])

  const updateSettings = async (partial) => {
    const next = { ...(settings || {}), ...partial }
    setSettings(next)
    await fetch(`${apiUrl}/api/settings`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(next) })
  }

  const simulate = async (user, text, eventType='chat') => {
    console.log('Sending test message:', { user, text, eventType })
    const fd = new FormData()
    fd.set('user', user)
    fd.set('text', text)
    fd.set('eventType', eventType)
    
    try {
      const response = await fetch(`${apiUrl}/api/simulate`, { method: 'POST', body: fd })
      const result = await response.json()
      console.log('Simulate response:', result)
    } catch (error) {
      console.error('Simulate error:', error)
    }
  }

  if (!settings) return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-400 mx-auto mb-4"></div>
        <p className="text-purple-200 text-lg">Loading Settings...</p>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white font-sans">
      <div className="container mx-auto px-6 py-8 max-w-6xl">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent mb-4">
            Chat Yapper Settings
          </h1>
          <p className="text-slate-300 text-lg">Configure your text-to-speech and avatar experience</p>
        </div>

        <section className="mb-8">
          <div className="bg-white/10 backdrop-blur-lg rounded-3xl p-8 shadow-2xl border border-white/20">
            <div className="flex items-center gap-4 mb-6">
              <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-500 rounded-2xl flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-white">Avatar Layout Settings</h2>
            </div>
            <div className="grid md:grid-cols-2 gap-8">
              <div className="space-y-3">
                <label className="text-sm font-semibold text-purple-200 uppercase tracking-wide">Number of Avatar Rows</label>
                <input 
                  type="number" 
                  min="1" 
                  max="10" 
                  className="w-full bg-white/10 backdrop-blur rounded-xl p-4 text-white placeholder-purple-300 border border-white/20 focus:border-purple-400 focus:outline-none focus:ring-2 focus:ring-purple-400/50 transition-all duration-200"
                  value={settings.avatarRows || 2}
                onChange={e => {
                  const newRows = parseInt(e.target.value) || 2
                  const currentRowConfig = settings.avatarRowConfig || [6, 6]
                  
                  // Adjust the row configuration array to match the new number of rows
                  let newRowConfig = [...currentRowConfig]
                  if (newRows > currentRowConfig.length) {
                    // Add new rows with default 6 avatars each
                    while (newRowConfig.length < newRows) {
                      newRowConfig.push(6)
                    }
                  } else if (newRows < currentRowConfig.length) {
                    // Remove excess rows
                    newRowConfig = newRowConfig.slice(0, newRows)
                  }
                  
                  updateSettings({ 
                    avatarRows: newRows,
                    avatarRowConfig: newRowConfig
                  })
                }}
                />
              </div>

              <div className="space-y-3">
                <label className="text-sm font-semibold text-purple-200 uppercase tracking-wide">Avatar Size</label>
                <input 
                  type="number" 
                  min="20" 
                  max="200" 
                  className="w-full bg-white/10 backdrop-blur rounded-xl p-4 text-white placeholder-purple-300 border border-white/20 focus:border-purple-400 focus:outline-none focus:ring-2 focus:ring-purple-400/50 transition-all duration-200"
                  value={settings.avatarSize || 60}
                  onChange={e => updateSettings({ avatarSize: parseInt(e.target.value) || 60 })}
                />
                <p className="text-xs text-purple-300">Size in pixels (20-200)</p>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-8">
              <div className="space-y-3">
                <label className="text-sm font-semibold text-purple-200 uppercase tracking-wide">Avatar Spacing</label>
                <input 
                  type="number" 
                  min="10" 
                  max="200" 
                  className="w-full bg-white/10 backdrop-blur rounded-xl p-4 text-white placeholder-purple-300 border border-white/20 focus:border-purple-400 focus:outline-none focus:ring-2 focus:ring-purple-400/50 transition-all duration-200"
                  value={settings.avatarSpacing || 50}
                  onChange={e => updateSettings({ avatarSpacing: parseInt(e.target.value) || 50 })}
                />
                <p className="text-xs text-purple-300">Space between avatars in pixels</p>
              </div>

              <div className="space-y-3">
                <label className="text-sm font-semibold text-purple-200 uppercase tracking-wide">Total Avatars</label>
                <div className="bg-gradient-to-r from-purple-600/20 to-pink-600/20 rounded-xl p-4 border border-purple-400/30">
                  <div className="text-2xl font-bold text-white text-center">
                    {(settings.avatarRowConfig || [6, 6]).slice(0, settings.avatarRows || 2).reduce((sum, count) => sum + count, 0)}
                  </div>
                  <p className="text-xs text-purple-300 text-center mt-1">Active avatar slots</p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <label className="text-sm font-semibold text-purple-200 uppercase tracking-wide">Individual Row Configuration</label>
              <div className="grid gap-4">
                {(settings.avatarRowConfig || [6, 6]).slice(0, settings.avatarRows || 2).map((avatarsInRow, rowIndex) => (
                  <div key={rowIndex} className="flex items-center gap-4 bg-white/5 backdrop-blur rounded-xl p-4 border border-white/10">
                    <label className="text-sm font-medium text-purple-200 w-20">Row {rowIndex + 1}</label>
                    <input 
                      type="number" 
                      min="1" 
                      max="20" 
                      className="flex-1 bg-white/10 backdrop-blur rounded-xl p-3 text-white placeholder-purple-300 border border-white/20 focus:border-purple-400 focus:outline-none focus:ring-2 focus:ring-purple-400/50 transition-all duration-200"
                      value={avatarsInRow}
                      onChange={e => {
                        const newConfig = [...(settings.avatarRowConfig || [6, 6])]
                        newConfig[rowIndex] = parseInt(e.target.value) || 1
                        updateSettings({ avatarRowConfig: newConfig })
                      }}
                    />
                    <span className="text-xs text-purple-300 w-16">avatars</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="mb-8">
          <div className="bg-white/10 backdrop-blur-lg rounded-3xl p-8 shadow-2xl border border-white/20">
            <div className="flex items-center gap-4 mb-8">
              <div className="w-12 h-12 bg-gradient-to-r from-green-500 to-blue-500 rounded-2xl flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-white">Text-to-Speech Providers</h2>
            </div>
          


            <div className="grid lg:grid-cols-2 gap-6">
              {/* MonsterTTS Configuration */}
              <div className="bg-gradient-to-br from-blue-600/20 to-purple-600/20 rounded-2xl p-6 border border-blue-400/30">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-bold text-blue-300">MonsterTTS</h3>
                  <span className="bg-gradient-to-r from-blue-500 to-purple-500 text-white text-xs px-3 py-1 rounded-full font-semibold">Premium</span>
                </div>
                <p className="text-sm text-blue-200 mb-6">High-quality AI voices with rate limiting. Falls back to configured voices when rate limited.</p>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-semibold text-blue-200 mb-2 uppercase tracking-wide">API Key</label>
                    <input 
                      className="w-full bg-white/10 backdrop-blur rounded-xl p-4 text-white placeholder-blue-300 border border-blue-400/30 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-400/50 transition-all duration-200" 
                      type="password"
                      placeholder="ttsm_12345-abcdef"
                      value={settings.tts?.monstertts?.apiKey || ''}
                      onChange={e => updateSettings({ 
                        tts: { 
                          ...settings.tts, 
                          monstertts: { 
                            ...settings.tts?.monstertts, 
                            apiKey: e.target.value 
                          } 
                        } 
                      })} />
                  </div>
                  
                  <div className="bg-blue-900/30 rounded-xl p-4 border border-blue-400/20">
                    <p className="text-xs text-blue-200">
                      Get your API key at <a href="https://tts.monster/" target="_blank" rel="noopener noreferrer" className="text-blue-300 hover:text-blue-200 underline font-semibold">tts.monster</a>
                    </p>
                  </div>
                </div>
              </div>

              {/* Edge TTS Configuration */}
              <div className="bg-gradient-to-br from-green-600/20 to-teal-600/20 rounded-2xl p-6 border border-green-400/30">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-bold text-green-300">Edge TTS</h3>
                  <span className="bg-gradient-to-r from-green-500 to-teal-500 text-white text-xs px-3 py-1 rounded-full font-semibold">Free</span>
                </div>
                <p className="text-sm text-green-200">Microsoft's Edge TTS service provides natural-sounding voices at no cost.</p>
              </div>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
              {/* Google TTS Configuration */}
              <div className="bg-gradient-to-br from-orange-600/20 to-red-600/20 rounded-2xl p-6 border border-orange-400/30">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-bold text-orange-300">Google Cloud TTS</h3>
                  <span className="bg-gradient-to-r from-orange-500 to-red-500 text-white text-xs px-3 py-1 rounded-full font-semibold">Paid</span>
                </div>
                <p className="text-sm text-orange-200 mb-6">Google's high-quality neural voices. Requires API key and billing account.</p>
                
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-semibold text-orange-200 mb-2 uppercase tracking-wide">API Key</label>
                    <input 
                      className="w-full bg-white/10 backdrop-blur rounded-xl p-4 text-white placeholder-orange-300 border border-orange-400/30 focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-400/50 transition-all duration-200" 
                      type="password"
                      placeholder="AIzaSy..."
                      value={settings.tts?.google?.apiKey || ''}
                      onChange={e => updateSettings({ 
                        tts: { 
                          ...settings.tts, 
                          google: { 
                            ...settings.tts?.google, 
                            apiKey: e.target.value 
                          } 
                        } 
                      })} />
                  </div>
                  
                  <div className="bg-orange-900/30 rounded-xl p-4 border border-orange-400/20">
                    <p className="text-xs text-orange-200">
                      Create an API key at <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer" className="text-orange-300 hover:text-orange-200 underline font-semibold">Google Cloud Console</a>
                    </p>
                  </div>
                </div>
              </div>

          {/* Amazon Polly Configuration - COMMENTED OUT (Not Working) */}
          {/*
          <div className="space-y-4 p-4 bg-neutral-800 rounded-lg opacity-60">
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-purple-400">Amazon Polly Settings</h3>
              <span className="text-xs bg-red-600 text-white px-2 py-1 rounded-full">Temporarily Disabled</span>
            </div>
            <p className="text-sm opacity-70">Amazon's lifelike TTS voices. Currently disabled due to authentication complexity - will be re-enabled in a future update.</p>
            
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-sm font-medium opacity-90">Access Key ID</label>
                <input 
                  className="w-full bg-neutral-700 rounded-lg p-3 text-sm border border-neutral-600 focus:border-purple-500 focus:outline-none" 
                  type="password"
                  placeholder="AKIA..."
                  value={settings.tts?.polly?.accessKey || ''}
                  onChange={e => updateSettings({ 
                    tts: { 
                      ...settings.tts, 
                      polly: { 
                        ...settings.tts?.polly, 
                        accessKey: e.target.value 
                      } 
                    } 
                  })} />
              </div>
              
              <div className="space-y-1">
                <label className="text-sm font-medium opacity-90">Secret Access Key</label>
                <input 
                  className="w-full bg-neutral-700 rounded-lg p-3 text-sm border border-neutral-600 focus:border-purple-500 focus:outline-none" 
                  type="password"
                  placeholder="Secret key..."
                  value={settings.tts?.polly?.secretKey || ''}
                  onChange={e => updateSettings({ 
                    tts: { 
                      ...settings.tts, 
                      polly: { 
                        ...settings.tts?.polly, 
                        secretKey: e.target.value 
                      } 
                    } 
                  })} />
              </div>
            </div>
            
            <div className="space-y-1">
              <label className="text-sm font-medium opacity-90">AWS Region</label>
              <select 
                className="w-full bg-neutral-700 rounded-lg p-3 text-sm border border-neutral-600 focus:border-purple-500 focus:outline-none"
                value={settings.tts?.polly?.region || 'us-east-1'}
                onChange={e => updateSettings({ 
                  tts: { 
                    ...settings.tts, 
                    polly: { 
                      ...settings.tts?.polly, 
                      region: e.target.value 
                    } 
                  } 
                })}>
                <option value="us-east-1">US East (N. Virginia)</option>
                <option value="us-west-2">US West (Oregon)</option>
                <option value="eu-west-1">Europe (Ireland)</option>
                <option value="ap-southeast-2">Asia Pacific (Sydney)</option>
              </select>
            </div>
            
            <div className="p-3 bg-neutral-700 rounded-lg">
              <p className="text-xs opacity-80">
                💡 Get AWS credentials at <a href="https://console.aws.amazon.com/iam/home#/security_credentials" target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:text-purple-300 underline">AWS Console</a>.
                Make sure your IAM user has Polly permissions.
              </p>
            </div>
          </div>
          */}

          {/* Web Speech API Configuration */}
          <div className="space-y-4 p-4 bg-neutral-800 rounded-lg">
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-teal-400">Web Speech API Settings</h3>
              <span className="text-xs bg-teal-600 text-white px-2 py-1 rounded-full">Free</span>
            </div>
            </div>
          </div>
        </section>

      <section className="mb-6">
        <div className="bg-neutral-900 rounded-2xl p-6 shadow">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">�️</span>
            Voice Management
          </h2>
          <VoiceManager />
        </div>
      </section>

      <section className="mb-6">
        <div className="bg-neutral-900 rounded-2xl p-6 shadow">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">�🎯</span>
            Special Event Voices
          </h2>
          <p className="text-sm opacity-70 mb-4">Assign specific voices to different Twitch events</p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { key: 'raid', name: 'Raids', icon: '⚔️', desc: 'When someone raids your stream' },
              { key: 'bits', name: 'Bits/Cheers', icon: '💎', desc: 'When viewers donate bits' },
              { key: 'sub', name: 'Subscriptions', icon: '⭐', desc: 'New subscribers' },
              { key: 'highlight', name: 'Highlights', icon: '✨', desc: 'Highlighted messages' },
              { key: 'vip', name: 'VIP Messages', icon: '👑', desc: 'Messages from VIPs' }
            ].map(event => (
              <div key={event.key} className="bg-neutral-800 rounded-lg p-4 space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{event.icon}</span>
                  <div>
                    <div className="font-medium text-sm">{event.name}</div>
                    <div className="text-xs opacity-60">{event.desc}</div>
                  </div>
                </div>
                <select 
                  className="w-full bg-neutral-700 rounded-lg p-2 text-sm border border-neutral-600 focus:border-blue-500 focus:outline-none"
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
        </div>
      </section>

      <section className="mb-6">
        <div className="bg-neutral-900 rounded-2xl p-6 shadow">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">🟣</span>
            Twitch Integration
          </h2>
          
          <div className="mb-4">
            <label className="flex items-center gap-3 p-4 bg-neutral-800 rounded-lg hover:bg-neutral-750 transition-colors cursor-pointer">
              <input 
                type="checkbox" 
                checked={!!settings.twitch?.enabled}
                onChange={e => updateSettings({ twitch: { ...settings.twitch, enabled: e.target.checked } })}
                className="w-4 h-4" 
              />
              <div>
                <div className="font-medium">Enable Twitch Bot</div>
                <div className="text-xs opacity-70">Connect to your Twitch chat for live TTS</div>
              </div>
            </label>
          </div>

          {settings.twitch?.enabled && (
            <div className="space-y-4 p-4 bg-neutral-800 rounded-lg">
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-sm font-medium opacity-90">Channel Name</label>
                  <input 
                    className="w-full bg-neutral-700 rounded-lg p-3 text-sm border border-neutral-600 focus:border-purple-500 focus:outline-none" 
                    placeholder="your_channel_name"
                    value={settings.twitch?.channel || ''}
                    onChange={e => updateSettings({ twitch: { ...settings.twitch, channel: e.target.value } })} />
                </div>
                
                <div className="space-y-1">
                  <label className="text-sm font-medium opacity-90">Bot Nickname</label>
                  <input 
                    className="w-full bg-neutral-700 rounded-lg p-3 text-sm border border-neutral-600 focus:border-purple-500 focus:outline-none" 
                    placeholder="your_bot_username"
                    value={settings.twitch?.nick || ''}
                    onChange={e => updateSettings({ twitch: { ...settings.twitch, nick: e.target.value } })} />
                </div>
              </div>
              
              <div className="space-y-1">
                <label className="text-sm font-medium opacity-90">OAuth Token</label>
                <input 
                  className="w-full bg-neutral-700 rounded-lg p-3 text-sm border border-neutral-600 focus:border-purple-500 focus:outline-none" 
                  placeholder="oauth:your_token_here"
                  type="password"
                  value={settings.twitch?.token || ''}
                  onChange={e => updateSettings({ twitch: { ...settings.twitch, token: e.target.value } })} />
              </div>
              
              <div className="p-3 bg-neutral-700 rounded-lg">
                <p className="text-xs opacity-80">
                  💡 Get your OAuth token at <a href="https://twitchtokengenerator.com/" target="_blank" rel="noopener noreferrer" className="text-purple-400 hover:text-purple-300 underline">twitchtokengenerator.com</a> with "chat:read" scope
                </p>
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="bg-neutral-900 rounded-2xl p-6 shadow mb-6">
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <span className="text-2xl">🧪</span>
          Test Simulator
        </h2>
        <p className="text-sm opacity-70 mb-4">Test your TTS configuration with sample messages</p>
        <Simulator onSend={simulate} />
      </section>

      <section className="bg-neutral-900 rounded-2xl p-6 shadow mb-6">
        <VoiceDistributionStats />
      </section>

      <section className="bg-neutral-900 rounded-2xl p-6 shadow">
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <span className="text-2xl">📋</span>
          Recent Activity
        </h2>
        <div className="text-center py-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-purple-600 to-pink-600 rounded-full mb-4">
            <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path d="M18 3a1 1 0 00-1.196-.98L5 4v9a4 4 0 110 2V4a1 1 0 011.196-.98L18 1a1 1 0 011 1v14a1 1 0 01-1 1z"/>
            </svg>
          </div>
          <p className="text-slate-400">Activity will appear here when TTS messages are played</p>
        </div>
      </section>
      </div>
    </div>
  )
}

function VoiceManager() {
  const [voices, setVoices] = useState([])
  const [availableVoices, setAvailableVoices] = useState({ monstertts: [], edge: [], google: [], polly: [], webspeech: [] })
  const [showAddForm, setShowAddForm] = useState(false)
  const [selectedProvider, setSelectedProvider] = useState('edge')
  const [selectedVoice, setSelectedVoice] = useState('')
  const [loadingMonsterVoices, setLoadingMonsterVoices] = useState(false)
  const [monsterError, setMonsterError] = useState('')

  // Determine the correct API URL
  const apiUrl = location.hostname === 'localhost' && (location.port === '5173' || location.port === '5174')
    ? 'http://localhost:8000'
    : ''

  // Load voices on mount
  useEffect(() => {
    loadVoices()
    loadAvailableVoices()
  }, [])

  const loadVoices = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/voices`)
      const data = await response.json()
      setVoices(data.voices || [])
    } catch (error) {
      console.error('Failed to load voices:', error)
    }
  }

  const loadAvailableVoices = async () => {
    try {
      // Get settings first to check API keys
      const settingsResponse = await fetch(`${apiUrl}/api/settings`)
      const settingsData = await settingsResponse.json()
      
      // Load Edge TTS voices (no API key needed)
      const edgeResponse = await fetch(`${apiUrl}/api/available-voices/edge`)
      const edgeData = await edgeResponse.json()
      
      // MonsterTTS voices
      const monsterApiKey = settingsData?.tts?.monstertts?.apiKey
      let monsterData = { voices: [] }
      if (monsterApiKey) {
        setLoadingMonsterVoices(true)
        setMonsterError('')
        try {
          const monsterResponse = await fetch(`${apiUrl}/api/available-voices/monstertts?api_key=${encodeURIComponent(monsterApiKey)}`)
          monsterData = await monsterResponse.json()
          if (monsterData.error) {
            setMonsterError(monsterData.error)
          }
        } catch (error) {
          setMonsterError('Failed to load MonsterTTS voices')
        }
        setLoadingMonsterVoices(false)
      } else {
        setMonsterError('MonsterTTS API key not configured')
      }
      
      // Google TTS voices
      let googleData = { voices: [] }
      const googleApiKey = settingsData?.tts?.google?.apiKey
      if (googleApiKey) {
        try {
          const googleResponse = await fetch(`${apiUrl}/api/available-voices/google?api_key=${encodeURIComponent(googleApiKey)}`)
          googleData = await googleResponse.json()
          
          // If there's an error, fallback to common Google voices
          if (googleData.error) {
            googleData = {
              voices: [
                {"voice_id": "en-US-Neural2-A", "name": "Neural2-A - Female US"},
                {"voice_id": "en-US-Neural2-C", "name": "Neural2-C - Female US"},
                {"voice_id": "en-US-Neural2-D", "name": "Neural2-D - Male US"},
                {"voice_id": "en-US-Neural2-F", "name": "Neural2-F - Female US"},
                {"voice_id": "en-US-Standard-A", "name": "Standard-A - Female US"},
                {"voice_id": "en-US-Standard-B", "name": "Standard-B - Male US"},
                {"voice_id": "en-US-Standard-C", "name": "Standard-C - Female US"},
                {"voice_id": "en-US-Standard-D", "name": "Standard-D - Male US"},
                {"voice_id": "en-US-Wavenet-A", "name": "Wavenet-A - Female US"},
                {"voice_id": "en-US-Wavenet-B", "name": "Wavenet-B - Male US"},
                {"voice_id": "en-US-Wavenet-C", "name": "Wavenet-C - Female US"},
                {"voice_id": "en-US-Wavenet-D", "name": "Wavenet-D - Male US"}
              ]
            }
          }
        } catch (error) {
          console.error('Failed to load Google voices:', error)
          // Fallback to common voices on network error too
          googleData = {
            voices: [
              {"voice_id": "en-US-Neural2-F", "name": "Neural2-F - Female US"},
              {"voice_id": "en-US-Standard-A", "name": "Standard-A - Female US"},
              {"voice_id": "en-US-Wavenet-A", "name": "Wavenet-A - Female US"}
            ]
          }
        }
      } else {
        // Show sample voices even without API key so user knows the option exists
        googleData = {
          voices: [
            {"voice_id": "en-US-Neural2-F", "name": "Neural2-F - Female US (Configure API key to see all)"},
            {"voice_id": "en-US-Standard-A", "name": "Standard-A - Female US (Configure API key to see all)"},
            {"voice_id": "en-US-Wavenet-A", "name": "Wavenet-A - Female US (Configure API key to see all)"}
          ]
        }
      }
      
      // Amazon Polly voices
      let pollyData = { voices: [] }
      const pollyConfig = settingsData?.tts?.polly
      if (pollyConfig?.accessKey && pollyConfig?.secretKey) {
        try {
          const pollyResponse = await fetch(`${apiUrl}/api/available-voices/polly`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              accessKey: pollyConfig.accessKey,
              secretKey: pollyConfig.secretKey,
              region: pollyConfig.region || 'us-east-1'
            })
          })
          pollyData = await pollyResponse.json()
        } catch (error) {
          console.error('Failed to load Polly voices:', error)
        }
      }
      
      // Web Speech API voices (client-side, so we provide common options)
      const webspeechData = {
        voices: [
          { voice_id: "en-US", name: "Default US English" },
          { voice_id: "en-GB", name: "Default UK English" },
          { voice_id: "en-CA", name: "Default Canadian English" },
          { voice_id: "en-AU", name: "Default Australian English" },
          { voice_id: "es-ES", name: "Spanish" },
          { voice_id: "fr-FR", name: "French" },
          { voice_id: "de-DE", name: "German" },
          { voice_id: "it-IT", name: "Italian" },
          { voice_id: "pt-BR", name: "Portuguese" },
          { voice_id: "ja-JP", name: "Japanese" },
          { voice_id: "ko-KR", name: "Korean" },
          { voice_id: "zh-CN", name: "Chinese" }
        ]
      }
      
      setAvailableVoices({
        edge: edgeData.voices || [],
        monstertts: monsterData.voices || [],
        google: googleData.voices || [],
        polly: pollyData.voices || [],
        webspeech: webspeechData.voices || []
      })
    } catch (error) {
      console.error('Failed to load available voices:', error)
    }
  }

  const addVoice = async () => {
    if (!selectedVoice) return

    const voiceData = availableVoices[selectedProvider].find(v => v.voice_id === selectedVoice)
    if (!voiceData) return

    try {
      const response = await fetch(`${apiUrl}/api/voices`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: voiceData.name,
          voice_id: voiceData.voice_id,
          provider: selectedProvider,
          enabled: true
        })
      })

      if (response.ok) {
        loadVoices()
        setShowAddForm(false)
        setSelectedVoice('')
      }
    } catch (error) {
      console.error('Failed to add voice:', error)
    }
  }

  const toggleVoice = async (voiceId, enabled) => {
    try {
      await fetch(`${apiUrl}/api/voices/${voiceId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled })
      })
      loadVoices()
    } catch (error) {
      console.error('Failed to toggle voice:', error)
    }
  }

  const deleteVoice = async (voiceId) => {
    if (!confirm('Are you sure you want to delete this voice?')) return
    
    try {
      await fetch(`${apiUrl}/api/voices/${voiceId}`, {
        method: 'DELETE'
      })
      loadVoices()
    } catch (error) {
      console.error('Failed to delete voice:', error)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <p className="text-sm opacity-70">Manage your TTS voices from both providers</p>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="bg-blue-600 hover:bg-blue-700 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
        >
          {showAddForm ? 'Cancel' : '+ Add Voice'}
        </button>
      </div>

      {showAddForm && (
        <div className="bg-neutral-800 rounded-lg p-4 space-y-4">
          <h3 className="font-medium">Add New Voice</h3>
          
          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="text-sm font-medium opacity-90">Provider</label>
              <select
                className="w-full bg-neutral-700 rounded-lg p-3 text-sm border border-neutral-600 focus:border-blue-500 focus:outline-none"
                value={selectedProvider}
                onChange={e => {
                  setSelectedProvider(e.target.value)
                  setSelectedVoice('')
                }}
              >
                <option value="edge">Edge TTS (Free)</option>
                <option value="monstertts">MonsterTTS (Premium)</option>
                <option value="google">Google Cloud TTS</option>
                <option value="polly" disabled>Amazon Polly (Temporarily Disabled)</option>
                <option value="webspeech">Web Speech API</option>
              </select>
            </div>
            
            <div className="space-y-1">
              <label className="text-sm font-medium opacity-90">Voice</label>
              {selectedProvider === 'monstertts' && loadingMonsterVoices ? (
                <div className="w-full bg-neutral-700 rounded-lg p-3 text-sm border border-neutral-600 flex items-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                  <span>Loading MonsterTTS voices...</span>
                </div>
              ) : selectedProvider === 'monstertts' && monsterError ? (
                <div className="w-full bg-red-900/20 border border-red-500/30 rounded-lg p-3 text-sm">
                  <div className="text-red-400 text-xs">{monsterError}</div>
                  <div className="text-xs opacity-70 mt-1">
                    Please configure your MonsterTTS API key in the TTS settings above.
                  </div>
                </div>
              ) : (
                <select
                  className="w-full bg-neutral-700 rounded-lg p-3 text-sm border border-neutral-600 focus:border-blue-500 focus:outline-none"
                  value={selectedVoice}
                  onChange={e => setSelectedVoice(e.target.value)}
                >
                  <option value="">Select a voice...</option>
                  {availableVoices[selectedProvider]?.map(voice => (
                    <option key={voice.voice_id} value={voice.voice_id}>
                      {voice.name}
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>
          
          <div className="flex justify-end">
            <button
              onClick={addVoice}
              disabled={!selectedVoice}
              className="bg-green-600 hover:bg-green-700 disabled:bg-neutral-600 disabled:cursor-not-allowed rounded-lg px-4 py-2 text-sm font-medium transition-colors"
            >
              Add Voice
            </button>
          </div>
        </div>
      )}

      <div className="space-y-2">
        <h3 className="font-medium text-sm opacity-90">Configured Voices ({voices.length})</h3>
        
        {voices.length === 0 ? (
          <div className="text-center p-8 text-neutral-400">
            <span className="text-3xl block mb-2">🎤</span>
            <p className="font-medium mb-2">No voices configured yet.</p>
            <p className="text-sm mb-4">Click "Add Voice" above to get started with TTS!</p>
            <div className="text-xs bg-neutral-800 rounded-lg p-3 text-left max-w-md mx-auto">
              <p className="font-medium mb-1">Quick Start:</p>
              <p>1. Click "Add Voice" above</p>
              <p>2. Select "Edge TTS (Free)" for instant setup</p>
              <p>3. Choose any voice and click "Add Voice"</p>
              <p>4. Test it with the simulator below!</p>
            </div>
          </div>
        ) : (
          <div className="grid gap-2">
            {voices.map(voice => (
              <div
                key={voice.id}
                className={`flex items-center justify-between p-3 rounded-lg transition-colors ${
                  voice.enabled ? 'bg-neutral-800 border border-green-500/30' : 'bg-neutral-800/50 border border-neutral-600'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-3 h-3 rounded-full ${voice.enabled ? 'bg-green-500' : 'bg-neutral-500'}`}></div>
                  <div>
                    <div className="font-medium text-sm">{voice.name}</div>
                    <div className="text-xs opacity-60 flex items-center gap-2">
                      <span className={
                        voice.provider === 'monstertts' ? 'text-blue-400' :
                        voice.provider === 'edge' ? 'text-green-400' :
                        voice.provider === 'google' ? 'text-orange-400' :
                        voice.provider === 'polly' ? 'text-purple-400' :
                        voice.provider === 'webspeech' ? 'text-teal-400' : 'text-gray-400'
                      }>
                        {voice.provider === 'monstertts' ? '🤖 MonsterTTS' :
                         voice.provider === 'edge' ? '🔄 Edge TTS' :
                         voice.provider === 'google' ? '🔊 Google TTS' :
                         voice.provider === 'polly' ? '🗣️ Amazon Polly' :
                         voice.provider === 'webspeech' ? '💬 Web Speech' : 
                         `📢 ${voice.provider}`}
                      </span>
                      <span>•</span>
                      <span>{voice.voice_id}</span>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => toggleVoice(voice.id, !voice.enabled)}
                    className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                      voice.enabled
                        ? 'bg-green-600 hover:bg-green-700 text-white'
                        : 'bg-neutral-600 hover:bg-neutral-500 text-neutral-200'
                    }`}
                  >
                    {voice.enabled ? 'Enabled' : 'Disabled'}
                  </button>
                  
                  <button
                    onClick={() => deleteVoice(voice.id)}
                    className="px-3 py-1 rounded text-xs font-medium bg-red-600 hover:bg-red-700 text-white transition-colors"
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function VoiceDistributionStats() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)

  // Determine the correct API URL
  const apiUrl = location.hostname === 'localhost' && (location.port === '5173' || location.port === '5174')
    ? 'http://localhost:8000'
    : ''

  const loadStats = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${apiUrl}/api/voice-stats`)
      const data = await response.json()
      setStats(data)
    } catch (error) {
      console.error('Failed to load voice stats:', error)
    }
    setLoading(false)
  }

  const resetStats = async () => {
    if (!confirm('Are you sure you want to reset voice distribution statistics?')) return
    
    try {
      await fetch(`${apiUrl}/api/voice-stats`, { method: 'DELETE' })
      setStats(null)
    } catch (error) {
      console.error('Failed to reset voice stats:', error)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <span className="text-2xl">📊</span>
            Voice Distribution Statistics
          </h2>
          <p className="text-sm opacity-70 mt-1">Track which random voices are being selected</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={loadStats}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-neutral-600 disabled:cursor-not-allowed rounded-lg px-4 py-2 text-sm font-medium transition-colors"
          >
            {loading ? 'Loading...' : 'Refresh Stats'}
          </button>
          {stats && (
            <button
              onClick={resetStats}
              className="bg-red-600 hover:bg-red-700 rounded-lg px-4 py-2 text-sm font-medium transition-colors"
            >
              Reset Stats
            </button>
          )}
        </div>
      </div>

      {!stats ? (
        <div className="text-center p-8 text-neutral-400">
          <span className="text-3xl block mb-2">📊</span>
          <p className="font-medium mb-2">No statistics available yet.</p>
          <p className="text-sm mb-4">Send some test messages to see voice distribution!</p>
          <button
            onClick={loadStats}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-neutral-600 disabled:cursor-not-allowed rounded-lg px-4 py-2 text-sm font-medium transition-colors"
          >
            {loading ? 'Loading...' : 'Load Stats'}
          </button>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-6">
          {/* Main Voice Selections */}
          <div className="bg-neutral-800 rounded-lg p-4">
            <h3 className="font-medium text-green-400 mb-3 flex items-center gap-2">
              <span>🎯</span>
              Primary Voice Selections
            </h3>
            <p className="text-xs opacity-70 mb-3">
              Total: {stats.main_selections.total_count} selections
            </p>
            
            {Object.keys(stats.main_selections.distribution).length === 0 ? (
              <p className="text-sm opacity-60 text-center py-4">No selections yet</p>
            ) : (
              <div className="space-y-2">
                {Object.entries(stats.main_selections.distribution)
                  .sort(([,a], [,b]) => b.count - a.count)
                  .map(([voiceName, data]) => (
                    <div key={voiceName} className="flex items-center justify-between text-sm">
                      <span className="truncate flex-1 mr-2">{voiceName}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-green-400 font-medium">{data.count}x</span>
                        <span className="text-xs opacity-70 w-12 text-right">
                          {data.percentage.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </div>

          {/* Fallback Voice Selections */}
          <div className="bg-neutral-800 rounded-lg p-4">
            <h3 className="font-medium text-orange-400 mb-3 flex items-center gap-2">
              <span>🔄</span>
              Fallback Voice Selections
            </h3>
            <p className="text-xs opacity-70 mb-3">
              Total: {stats.fallback_selections.total_count} fallbacks
            </p>
            
            {Object.keys(stats.fallback_selections.distribution).length === 0 ? (
              <p className="text-sm opacity-60 text-center py-4">No fallbacks yet</p>
            ) : (
              <div className="space-y-2">
                {Object.entries(stats.fallback_selections.distribution)
                  .sort(([,a], [,b]) => b.count - a.count)
                  .map(([voiceName, data]) => (
                    <div key={voiceName} className="flex items-center justify-between text-sm">
                      <span className="truncate flex-1 mr-2">{voiceName}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-orange-400 font-medium">{data.count}x</span>
                        <span className="text-xs opacity-70 w-12 text-right">
                          {data.percentage.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </div>
        </div>
      )}

      {stats && (stats.main_selections.total_count > 0 || stats.fallback_selections.total_count > 0) && (
        <div className="bg-neutral-800 rounded-lg p-4">
          <h4 className="font-medium text-blue-400 mb-2">📈 Quick Analysis</h4>
          <div className="text-xs opacity-70 space-y-1">
            <p>• Primary selections show the distribution of your main voice choices</p>
            <p>• Fallback selections occur when providers fail or are rate-limited</p>
            <p>• A truly random distribution should show roughly equal percentages across all voices</p>
            {stats.fallback_selections.total_count > 0 && (
              <p>• High fallback count may indicate provider reliability issues</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function Simulator({ onSend }) {
  const [user, setUser] = useState('TestUser')
  const [text, setText] = useState('Hello Chat Yappers!')
  const [eventType, setEventType] = useState('chat')
  
  const eventTypes = [
    { value: 'chat', label: '💬 Chat', desc: 'Regular chat message' },
    { value: 'raid', label: '⚔️ Raid', desc: 'Raid event' },
    { value: 'bits', label: '💎 Bits', desc: 'Bits/Cheers' },
    { value: 'sub', label: '⭐ Subscribe', desc: 'New subscription' },
    { value: 'highlight', label: '✨ Highlight', desc: 'Highlighted message' },
    { value: 'vip', label: '👑 VIP', desc: 'VIP message' }
  ]
  
  return (
    <div className="space-y-4">
      <div className="grid md:grid-cols-3 gap-4">
        <div className="space-y-1">
          <label className="text-sm font-medium opacity-90">Username</label>
          <input 
            className="w-full bg-neutral-800 rounded-lg p-3 text-sm border border-neutral-700 focus:border-blue-500 focus:outline-none" 
            placeholder="TestUser"
            value={user} 
            onChange={e => setUser(e.target.value)} />
        </div>
        
        <div className="space-y-1 md:col-span-2">
          <label className="text-sm font-medium opacity-90">Message</label>
          <input 
            className="w-full bg-neutral-800 rounded-lg p-3 text-sm border border-neutral-700 focus:border-blue-500 focus:outline-none" 
            placeholder="Type your test message here..."
            value={text} 
            onChange={e => setText(e.target.value)} />
        </div>
      </div>
      
      <div className="space-y-1">
        <label className="text-sm font-medium opacity-90">Event Type</label>
        <select 
          className="w-full bg-neutral-800 rounded-lg p-3 text-sm border border-neutral-700 focus:border-blue-500 focus:outline-none" 
          value={eventType} 
          onChange={e => setEventType(e.target.value)}>
          {eventTypes.map(type => 
            <option key={type.value} value={type.value}>{type.label} - {type.desc}</option>
          )}
        </select>
      </div>
      
      <div className="flex justify-center pt-2">
        <button 
          className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 transition-all duration-200 rounded-lg px-8 py-3 font-medium flex items-center gap-2 shadow-lg" 
          onClick={() => onSend(user, text, eventType)}
        >
          <span className="text-lg">🚀</span>
          Send Test Message
        </button>
      </div>
    </div>
  )
}
