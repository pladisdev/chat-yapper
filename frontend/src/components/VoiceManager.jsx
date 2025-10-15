import React, { useEffect, useState } from 'react'
import logger from '../utils/logger'

export default function VoiceManager({ managedAvatars, apiUrl }) {
  const [voices, setVoices] = useState([])
  const [availableVoices, setAvailableVoices] = useState({ monstertts: [], google: [], polly: [], edge: [] })
  const [showAddForm, setShowAddForm] = useState(false)
  const [selectedProvider, setSelectedProvider] = useState('edge')
  const [selectedVoice, setSelectedVoice] = useState('')
  const [loadingMonsterVoices, setLoadingMonsterVoices] = useState(false)
  const [monsterError, setMonsterError] = useState('')
  const [googleError, setGoogleError] = useState('')
  const [pollyError, setPollyError] = useState('')

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
      setGoogleError('')  // Clear previous errors
      
      if (googleApiKey) {
        try {
          const googleResponse = await fetch(`${apiUrl}/api/available-voices/google?api_key=${encodeURIComponent(googleApiKey)}`)
          googleData = await googleResponse.json()

          logger.info(googleData);
          
          
          // If there's an error, don't show any voices - user needs to fix the API key
          if (googleData.error) {
            console.error('Failed to fetch Google voices:', googleData.error)
            setGoogleError(googleData.error)
            googleData = { voices: [] }
          }
        } catch (error) {
          console.error('Failed to fetch Google voices:', error)
          setGoogleError(`Failed to connect: ${error.message}`)
          googleData = { voices: [] }
        }
      } else {
        setGoogleError('No API key configured')
      }
      // If no API key or error, don't show any voices
      
      // Amazon Polly voices
      let pollyData = { voices: [] }
      const pollyConfig = settingsData?.tts?.polly
      setPollyError('')  // Clear previous errors
      
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
          
          if (pollyData.error) {
            console.error('Failed to fetch Polly voices:', pollyData.error)
            setPollyError(pollyData.error)
            pollyData = { voices: [] }
          }
        } catch (error) {
          console.error('Failed to load Polly voices:', error)
          setPollyError(`Failed to connect: ${error.message}`)
          pollyData = { voices: [] }
        }
      } else {
        setPollyError('AWS credentials not configured')
        // No voices until credentials are configured
        pollyData = { voices: [] }
      }
      
      // Edge TTS voices (always available, no API key needed)
      let edgeData = { voices: [] }
      try {
        const edgeResponse = await fetch(`${apiUrl}/api/available-voices/edge`)
        edgeData = await edgeResponse.json()
      } catch (error) {
        console.error('Failed to load Edge TTS voices:', error)
        // Fallback to common Edge voices
        edgeData = {
          voices: [
            {"voice_id": "en-US-AvaNeural", "name": "Ava - Female US"},
            {"voice_id": "en-US-BrianNeural", "name": "Brian - Male US"},
            {"voice_id": "en-US-EmmaNeural", "name": "Emma - Female US"},
            {"voice_id": "en-US-JennyNeural", "name": "Jenny - Female US"},
            {"voice_id": "en-US-GuyNeural", "name": "Guy - Male US"}
          ]
        }
      }
    
      
      const newAvailableVoices = {
        monstertts: monsterData.voices || [],
        google: googleData.voices || [],
        polly: pollyData.voices || [],
        edge: edgeData.voices || [],
      }
      
      logger.info('📊 Available voices loaded:', {
        monstertts: newAvailableVoices.monstertts.length,
        google: newAvailableVoices.google.length,
        polly: newAvailableVoices.polly.length,
        edge: newAvailableVoices.edge.length
      })
      logger.info('🎤 Polly voices:', newAvailableVoices.polly)
      
      setAvailableVoices(newAvailableVoices)
    } catch (error) {
      console.error('Failed to load available voices:', error)
    }
  }

  const addVoice = async () => {
    if (!selectedVoice) {
      console.warn('No voice selected')
      return
    }

    console.log('🔍 Looking for voice:', selectedVoice, 'in provider:', selectedProvider)
    console.log('📋 Available voices for provider:', availableVoices[selectedProvider])
    
    const voiceData = availableVoices[selectedProvider].find(v => v.voice_id === selectedVoice)
    
    if (!voiceData) {
      console.error('❌ Voice not found! Selected:', selectedVoice, 'Available:', availableVoices[selectedProvider])
      return
    }
    
    console.log('✅ Found voice data:', voiceData)

    try {
      const voicePayload = {
        name: voiceData.name,
        voice_id: voiceData.voice_id,
        provider: selectedProvider,
        enabled: true
      }
      
      const response = await fetch(`${apiUrl}/api/voices`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(voicePayload)
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

  const testVoice = async (provider, voiceId, voiceName) => {
    try {
      logger.info(`Testing voice: ${voiceName} (${provider}, ${voiceId})`)
      
      // Create a temporary voice object for testing
      const testVoiceData = {
        provider: provider,
        voice_id: voiceId,
        name: voiceName,
        enabled: true
      }
      
      // Send test message using the simulate API
      const fd = new FormData()
      fd.set('user', 'VoiceTester')
      fd.set('text', 'I am a chat member')
      fd.set('eventType', 'chat')
      fd.set('testVoice', JSON.stringify(testVoiceData))
      
      const response = await fetch(`${apiUrl}/api/simulate`, { 
        method: 'POST', 
        body: fd 
      })
      
      if (response.ok) {
        logger.info('Voice test message sent successfully')
      } else {
        console.error('Failed to send voice test message:', response.status)
      }
    } catch (error) {
      console.error('Error testing voice:', error)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <p className="text-sm text-purple-300">Manage your TTS voices from multiple providers</p>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="bg-purple-600 hover:bg-purple-700 rounded-xl px-5 py-2.5 text-sm font-semibold transition-all shadow-lg hover:shadow-purple-500/50"
        >
          {showAddForm ? 'Cancel' : '+ Add Voice'}
        </button>
      </div>

      {showAddForm && (
        <div className="bg-white/5 backdrop-blur-sm rounded-xl border border-white/10 p-6 space-y-4">
          <h3 className="font-semibold text-white text-lg">Add New Voice</h3>
          
          <div className="grid md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-semibold text-purple-300">Provider</label>
              <select
                className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500 [&>option]:bg-gray-800 [&>option]:text-white"
                value={selectedProvider}
                onChange={e => {
                  setSelectedProvider(e.target.value)
                  setSelectedVoice('')
                }}
              >
                <option value="edge">Edge TTS (Free)</option>
                <option value="monstertts">MonsterTTS (Rated)</option>
                <option value="google">Google Cloud TTS (Rated)</option>
                <option value="polly">Amazon Polly (Rated)</option>
              </select>
            </div>
            
            <div className="space-y-2">
              <label className="text-sm font-semibold text-purple-300">Voice</label>
              {selectedProvider === 'monstertts' && loadingMonsterVoices ? (
                <div className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 flex items-center gap-2">
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-purple-500 border-t-transparent"></div>
                  <span className="text-white text-sm">Loading MonsterTTS voices...</span>
                </div>
              ) : selectedProvider === 'monstertts' && monsterError ? (
                <div className="w-full bg-red-900/20 border border-red-500/30 rounded-xl px-4 py-3">
                  <div className="text-red-300 text-sm">{monsterError}</div>
                  <div className="text-xs text-red-400 mt-1">
                    Please configure your MonsterTTS API key in the settings.
                  </div>
                </div>
              ) : selectedProvider === 'google' && googleError ? (
                <div className="w-full bg-red-900/20 border border-red-500/30 rounded-xl px-4 py-3">
                  <div className="text-red-300 text-sm">{googleError}</div>
                  <div className="text-xs text-red-400 mt-1">
                    Please configure your Google Cloud API key in the TTS settings.
                  </div>
                </div>
              ) : selectedProvider === 'polly' && pollyError ? (
                <div className="w-full bg-red-900/20 border border-red-500/30 rounded-xl px-4 py-3">
                  <div className="text-red-300 text-sm">{pollyError}</div>
                  <div className="text-xs text-red-400 mt-1">
                    Please configure your AWS Access Key and Secret Key in the TTS settings.
                  </div>
                </div>
              ) : (
                <select
                  className="w-full bg-white/10 border border-white/20 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-purple-500 [&>option]:bg-gray-800 [&>option]:text-white"
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
          
          <div className="flex justify-end gap-3">
            <button
              onClick={() => {
                if (selectedVoice) {
                  const voice = availableVoices[selectedProvider]?.find(v => v.voice_id === selectedVoice)
                  if (voice) {
                    testVoice(selectedProvider, selectedVoice, voice.name)
                  }
                }
              }}
              disabled={!selectedVoice}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-neutral-600 disabled:cursor-not-allowed rounded-xl px-5 py-2.5 text-sm font-semibold transition-all shadow-lg hover:shadow-blue-500/50 flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 14.142M13 12a1 1 0 11-2 0 1 1 0 012 0z" />
              </svg>
              Test Voice
            </button>
            <button
              onClick={addVoice}
              disabled={!selectedVoice}
              className="bg-green-600 hover:bg-green-700 disabled:bg-neutral-600 disabled:cursor-not-allowed rounded-xl px-5 py-2.5 text-sm font-semibold transition-all shadow-lg hover:shadow-green-500/50"
            >
              Add Voice
            </button>
          </div>
        </div>
      )}

      <div className="space-y-3">
        <h3 className="font-semibold text-white text-lg">Configured Voices ({voices.length})</h3>
        
        {voices.length === 0 ? (
          <div className="text-center p-12 bg-gradient-to-br from-purple-900/20 to-pink-900/20 rounded-xl border border-purple-500/30">
            <span className="text-5xl block mb-4">🎤</span>
            <p className="font-semibold text-xl text-white mb-2">No voices configured yet.</p>
            <p className="text-purple-300 mb-6">Click "Add Voice" above to get started with TTS!</p>
            <div className="text-sm bg-white/5 backdrop-blur-sm rounded-xl border border-white/10 p-5 text-left max-w-md mx-auto">
              <p className="font-semibold text-white mb-3">Quick Start:</p>
              <div className="space-y-2 text-purple-200">
                <p>1. Click "Add Voice" above</p>
                <p>2. Select "Edge TTS" (free, no setup required)</p>
                <p>3. Choose any voice and click "Add Voice"</p>
                <p>4. Test it with the simulator in the Testing tab!</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="grid gap-3">
            {voices.map(voice => (
              <div
                key={voice.id}
                className={`flex items-center justify-between p-4 rounded-xl transition-all ${
                  voice.enabled 
                    ? 'bg-gradient-to-r from-green-900/30 to-emerald-900/30 border border-green-500/40 shadow-lg' 
                    : 'bg-white/5 border border-white/10'
                }`}
              >
                <div className="flex items-center gap-4">
                  <div className={`w-4 h-4 rounded-full ${voice.enabled ? 'bg-green-500 shadow-lg shadow-green-500/50' : 'bg-neutral-500'}`}></div>
                  <div>
                    <div className="font-semibold text-white">{voice.name}</div>
                    <div className="text-sm text-purple-300 flex items-center gap-2 mt-1">
                      <span className={
                        voice.provider === 'monstertts' ? 'text-blue-400' :
                        voice.provider === 'google' ? 'text-orange-400' :
                        voice.provider === 'polly' ? 'text-purple-400' :
                        voice.provider === 'edge' ? 'text-green-400' : 'text-gray-400'
                      }>
                        {voice.provider === 'monstertts' ? 'MonsterTTS' :
                         voice.provider === 'google' ? 'Google TTS' :
                         voice.provider === 'polly' ? 'Amazon Polly' :
                         voice.provider === 'edge' ? 'Edge TTS' :
                         `${voice.provider}`}
                      </span>
                      <span>•</span>
                      <span className="text-purple-400">{voice.voice_id}</span>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => testVoice(voice.provider, voice.voice_id, voice.name)}
                    className="px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white transition-all shadow-lg hover:shadow-blue-500/50 flex items-center gap-2"
                    title="Test this voice with 'I am a chat member'"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 14.142M13 12a1 1 0 11-2 0 1 1 0 012 0z" />
                    </svg>
                    Test
                  </button>
                  
                  <button
                    onClick={() => toggleVoice(voice.id, !voice.enabled)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-all shadow-lg ${
                      voice.enabled
                        ? 'bg-green-600 hover:bg-green-700 text-white hover:shadow-green-500/50'
                        : 'bg-neutral-600 hover:bg-neutral-500 text-neutral-200 hover:shadow-neutral-500/50'
                    }`}
                  >
                    {voice.enabled ? 'Enabled' : 'Disabled'}
                  </button>
                  
                  <button
                    onClick={() => deleteVoice(voice.id)}
                    className="px-4 py-2 rounded-lg text-sm font-medium bg-red-600 hover:bg-red-700 text-white transition-all shadow-lg hover:shadow-red-500/50"
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
