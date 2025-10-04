import React, { useEffect, useState } from 'react'

export default function SettingsPage() {
  const [settings, setSettings] = useState(null)
  const [log, setLog] = useState([])
  const [allVoices, setAllVoices] = useState([])
  const [managedAvatars, setManagedAvatars] = useState([])
  const [uploading, setUploading] = useState(false)
  const [uploadMode, setUploadMode] = useState('single') // 'single' or 'pair'
  const [selectedAvatarGroup, setSelectedAvatarGroup] = useState('')
  const [avatarName, setAvatarName] = useState('')
  const [replacementInfo, setReplacementInfo] = useState(null) // Track what will be replaced

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
    
    // Load managed avatars
    fetch(`${apiUrl}/api/avatars/managed`).then(r => r.json()).then(data => {
      setManagedAvatars(data?.avatars || [])
    })
  }, [apiUrl])

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

    // Check for replacement and confirm if needed
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
      
      // For pair mode, use the selected group or create a new one
      if (uploadMode === 'pair') {
        const groupId = selectedAvatarGroup || `avatar_${Date.now()}`
        formData.append('avatar_group_id', groupId)
        
        // If this is a new group, update selected group for the second upload
        if (!selectedAvatarGroup) {
          setSelectedAvatarGroup(groupId)
        }
      }
      
      const response = await fetch(`${apiUrl}/api/avatars/upload`, {
        method: 'POST',
        body: formData
      })
      
      const result = await response.json()
      if (result.success) {
        // Reload managed avatars
        const avatarsResponse = await fetch(`${apiUrl}/api/avatars/managed`)
        const avatarsData = await avatarsResponse.json()
        setManagedAvatars(avatarsData?.avatars || [])
        
        // Clear form if single mode or if pair is complete
        if (uploadMode === 'single') {
          setAvatarName('')
        }
      } else {
        alert(`Upload failed: ${result.error}`)
      }
    } catch (error) {
      alert(`Upload error: ${error.message}`)
    } finally {
      setUploading(false)
      // Clear the file input
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
        // Reload managed avatars
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
        // Reload managed avatars
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

  if (!settings) return <div className="p-6 font-sans text-white">Loading…</div>

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 font-sans p-6">
      <h1 className="text-2xl font-bold mb-6">Chat Yapper Settings</h1>

      <section className="mb-6">
        <div className="bg-neutral-900 rounded-2xl p-6 shadow">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">⚙️</span>
            General Settings
          </h2>
          <div className="space-y-6">
            <div className="space-y-1">
              <label className="text-sm font-medium opacity-90">Number of Avatar Rows</label>
              <input 
                type="number" 
                min="1" 
                max="10" 
                className="w-full bg-neutral-800 rounded-lg p-3 text-sm border border-neutral-700 focus:border-blue-500 focus:outline-none"
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
              <label className="text-sm font-medium opacity-90">Avatars Per Row Configuration</label>
              <div className="space-y-2">
                {(settings.avatarRowConfig || [6, 6]).slice(0, settings.avatarRows || 2).map((avatarsInRow, rowIndex) => (
                  <div key={rowIndex} className="flex items-center gap-3">
                    <label className="text-sm opacity-70 w-16">Row {rowIndex + 1}:</label>
                    <input 
                      type="number" 
                      min="1" 
                      max="20" 
                      className="flex-1 bg-neutral-800 rounded-lg p-3 text-sm border border-neutral-700 focus:border-blue-500 focus:outline-none"
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
              <div className="text-xs opacity-60 bg-neutral-800 p-3 rounded-lg">
                💡 Configure how many avatars appear in each row. Total avatars: {(settings.avatarRowConfig || [6, 6]).slice(0, settings.avatarRows || 2).reduce((sum, count) => sum + count, 0)}
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium opacity-90">Avatar Size (px)</label>
              <input 
                type="number" 
                min="20" 
                max="200" 
                className="w-full bg-neutral-800 rounded-lg p-3 text-sm border border-neutral-700 focus:border-blue-500 focus:outline-none"
                value={settings.avatarSize || 60}
                onChange={e => updateSettings({ avatarSize: parseInt(e.target.value) || 60 })}
              />
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-sm font-medium opacity-90">Horizontal Avatar Spacing (px)</label>
                <input 
                  type="number" 
                  min="10" 
                  max="200" 
                  className="w-full bg-neutral-800 rounded-lg p-3 text-sm border border-neutral-700 focus:border-blue-500 focus:outline-none"
                  value={settings.avatarSpacingX || settings.avatarSpacing || 50}
                  onChange={e => updateSettings({ avatarSpacingX: parseInt(e.target.value) || 50 })}
                />
              </div>
              
              <div className="space-y-1">
                <label className="text-sm font-medium opacity-90">Vertical Avatar Spacing (px)</label>
                <input 
                  type="number" 
                  min="10" 
                  max="200" 
                  className="w-full bg-neutral-800 rounded-lg p-3 text-sm border border-neutral-700 focus:border-blue-500 focus:outline-none"
                  value={settings.avatarSpacingY || settings.avatarSpacing || 50}
                  onChange={e => updateSettings({ avatarSpacingY: parseInt(e.target.value) || 50 })}
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mb-6">
        <div className="bg-neutral-900 rounded-2xl p-6 shadow">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">🖼️</span>
            Avatar Management
          </h2>
          <p className="text-sm opacity-70 mb-4">Upload and manage avatar images for voices</p>
          
          <div className="space-y-4">
            {/* Upload Configuration */}
            <div className="bg-neutral-800 rounded-lg p-4 space-y-4">
              <h4 className="font-medium text-sm">Upload Configuration</h4>
              
              <div className="space-y-3">
                <div className="space-y-1">
                  <label className="text-sm font-medium opacity-90">Avatar Name</label>
                  <input 
                    type="text"
                    className="w-full bg-neutral-700 rounded-lg p-3 text-sm border border-neutral-600 focus:border-blue-500 focus:outline-none"
                    placeholder="Enter avatar name (e.g., 'Happy Cat', 'Serious Dog')"
                    value={avatarName}
                    onChange={e => setAvatarName(e.target.value)}
                  />
                  {avatarName.trim() && (() => {
                    const defaultCheck = checkForReplacement(avatarName.trim(), 'default')
                    const speakingCheck = checkForReplacement(avatarName.trim(), 'speaking')
                    const willReplace = defaultCheck.exists || speakingCheck.exists
                    
                    return willReplace ? (
                      <div className="text-xs text-yellow-400 mt-1 p-2 bg-yellow-900/20 rounded border border-yellow-500/30">
                        ⚠️ {uploadMode === 'single' && defaultCheck.exists && 'Will replace existing avatar'}
                        {uploadMode === 'pair' && defaultCheck.exists && speakingCheck.exists && 'Will replace existing avatar pair'}
                        {uploadMode === 'pair' && defaultCheck.exists && !speakingCheck.exists && 'Will replace default image, speaking image will be added'}
                        {uploadMode === 'pair' && !defaultCheck.exists && speakingCheck.exists && 'Will add default image, replace speaking image'}
                      </div>
                    ) : null
                  })()}
                </div>
                
                <div className="space-y-1">
                  <label className="text-sm font-medium opacity-90">Upload Mode</label>
                  <select
                    className="w-full bg-neutral-700 rounded-lg p-3 text-sm border border-neutral-600 focus:border-blue-500 focus:outline-none"
                    value={uploadMode}
                    onChange={e => {
                      setUploadMode(e.target.value)
                      setSelectedAvatarGroup('')
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
              <div className="bg-neutral-800 rounded-lg p-4">
                <label className="flex items-center justify-center w-full h-32 border-2 border-dashed border-neutral-600 rounded-lg cursor-pointer hover:border-neutral-500 transition-colors">
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
                        <div className="animate-spin w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                        <span className="text-sm">Uploading...</span>
                      </div>
                    ) : !avatarName.trim() ? (
                      <>
                        <div className="text-2xl mb-2">⚠️</div>
                        <div className="text-sm font-medium text-yellow-400">Enter avatar name first</div>
                        <div className="text-xs opacity-60 mt-1">Name is required before uploading</div>
                      </>
                    ) : (
                      <>
                        <div className="text-2xl mb-2">📁</div>
                        <div className="text-sm font-medium">Click to upload single avatar image</div>
                        <div className="text-xs opacity-60 mt-1">PNG, JPG, GIF up to 5MB</div>
                      </>
                    )}
                  </div>
                </label>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="bg-neutral-800 rounded-lg p-4">
                  <h5 className="text-sm font-medium mb-3">Default Image (Idle State)</h5>
                  <label className="flex items-center justify-center w-full h-24 border-2 border-dashed border-neutral-600 rounded-lg cursor-pointer hover:border-neutral-500 transition-colors">
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
                          <div className="animate-spin w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                          <span className="text-xs">Uploading...</span>
                        </div>
                      ) : !avatarName.trim() ? (
                        <div className="text-xs text-yellow-400">Enter name first</div>
                      ) : (
                        <>
                          <div className="text-lg mb-1">😴</div>
                          <div className="text-xs font-medium">Upload default image</div>
                        </>
                      )}
                    </div>
                  </label>
                </div>
                
                <div className="bg-neutral-800 rounded-lg p-4">
                  <h5 className="text-sm font-medium mb-3">Speaking Image (Active State)</h5>
                  <label className="flex items-center justify-center w-full h-24 border-2 border-dashed border-neutral-600 rounded-lg cursor-pointer hover:border-neutral-500 transition-colors">
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
                          <div className="animate-spin w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                          <span className="text-xs">Uploading...</span>
                        </div>
                      ) : !avatarName.trim() ? (
                        <div className="text-xs text-yellow-400">Enter name first</div>
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
              <div className="space-y-2">
                <h3 className="text-sm font-medium opacity-90">Uploaded Avatars</h3>
                <div className="space-y-4">
                  {(() => {
                    // Group avatars by group_id or treat singles individually
                    const grouped = {}
                    managedAvatars.forEach(avatar => {
                      const key = avatar.avatar_group_id || `single_${avatar.id}`
                      if (!grouped[key]) grouped[key] = []
                      grouped[key].push(avatar)
                    })
                    
                    return Object.entries(grouped).map(([groupKey, avatars]) => (
                      <div key={groupKey} className="bg-neutral-800 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-3">
                          <h4 className="font-medium text-sm">{avatars[0].name}</h4>
                          <button
                            onClick={() => handleDeleteAvatarGroup(groupKey, avatars[0].name, avatars.length > 1)}
                            className="text-xs text-red-400 hover:text-red-300 transition-colors"
                          >
                            Delete Avatar{avatars.length > 1 ? ' Pair' : ''}
                          </button>
                        </div>
                        
                        <div className="flex gap-3">
                          {avatars
                            .sort((a, b) => a.avatar_type === 'default' ? -1 : 1)
                            .map(avatar => (
                              <div key={avatar.id} className="text-center bg-neutral-700 rounded-lg p-3 relative group">
                                {/* Individual delete button for each image */}
                                {avatars.length > 1 && (
                                  <button
                                    onClick={() => handleDeleteAvatar(avatar.id)}
                                    className="absolute -top-1 -right-1 w-5 h-5 bg-red-600 hover:bg-red-700 text-white rounded-full text-xs opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center"
                                    title={`Delete ${avatar.avatar_type} image`}
                                  >
                                    ×
                                  </button>
                                )}
                                
                                <div className="w-16 h-16 bg-neutral-600 rounded-lg overflow-hidden avatar-container mb-2 mx-auto">
                                  <img 
                                    src={`${apiUrl}${avatar.file_path}`}
                                    alt={`${avatar.name} - ${avatar.avatar_type}`}
                                    className="w-full h-full avatar-image"
                                    onError={(e) => {
                                      e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100"><rect width="100" height="100" fill="%23374151"/><text x="50" y="50" text-anchor="middle" dy=".3em" fill="%23d1d5db" font-size="12">Error</text></svg>'
                                    }}
                                  />
                                </div>
                                <div className="text-xs opacity-80 font-medium">
                                  {avatar.avatar_type === 'default' ? '😴 Default' : '🗣️ Speaking'}
                                </div>
                                <div className="text-xs opacity-40 mt-1">
                                  {(avatar.file_size / 1024).toFixed(1)}KB
                                </div>
                              </div>
                            ))}
                        </div>
                      </div>
                    ))
                  })()}
                </div>
              </div>
            )}
            
            {managedAvatars.length === 0 && (
              <div className="text-center py-8 text-sm opacity-60">
                No avatars uploaded yet. Upload some images to get started!
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="mb-6">
        <div className="bg-neutral-900 rounded-2xl p-6 shadow">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">🎤</span>
            Text-to-Speech Configuration
          </h2>
          


          {/* MonsterTTS Configuration */}
          <div className="space-y-4 p-4 bg-neutral-800 rounded-lg">
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-blue-400">MonsterTTS Settings</h3>
            </div>
            <p className="text-sm opacity-70">AI voices with rate limiting (1 generation every 2 seconds). Falls back to random configured voice when rate limited.</p>
            
            <div className="space-y-1">
              <label className="text-sm font-medium opacity-90">API Key</label>
              <input 
                className="w-full bg-neutral-700 rounded-lg p-3 text-sm border border-neutral-600 focus:border-blue-500 focus:outline-none" 
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
                })} />
            </div>
            
            <div className="p-3 bg-neutral-700 rounded-lg">
              <p className="text-xs opacity-80">
                💡 Get your API key at <a href="https://tts.monster/" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300 underline">tts.monster</a>. 
                When rate limited, the system will automatically use a random voice from your configured voices below.
              </p>
            </div>
          </div>

          {/* Google TTS Configuration */}
          <div className="space-y-4 p-4 bg-neutral-800 rounded-lg">
            <div className="flex items-center gap-2">
              <h3 className="font-medium text-orange-400">Google Cloud TTS Settings</h3>
            </div>
            <p className="text-sm opacity-70">Google's neural voices. Requires API key and billing account.</p>
            
            <div className="space-y-1">
              <label className="text-sm font-medium opacity-90">API Key</label>
              <input 
                className="w-full bg-neutral-700 rounded-lg p-3 text-sm border border-neutral-600 focus:border-orange-500 focus:outline-none" 
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
                })} />
            </div>
            
            <div className="p-3 bg-neutral-700 rounded-lg">
              <p className="text-xs opacity-80">
                💡 Create an API key at <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener noreferrer" className="text-orange-400 hover:text-orange-300 underline">Google Cloud Console</a>.
                Enable the Text-to-Speech API for your project.
              </p>
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


        </div>
      </section>

      <section className="mb-6">
        <div className="bg-neutral-900 rounded-2xl p-6 shadow">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">�️</span>
            Voice Management
          </h2>
          <VoiceManager managedAvatars={managedAvatars} apiUrl={apiUrl} />
        </div>
      </section>

      <section className="mb-6">
        <div className="bg-neutral-900 rounded-2xl p-6 shadow">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">🎯</span>
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

      <section className="mb-6">
        <div className="bg-neutral-900 rounded-2xl p-6 shadow">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">🔇</span>
            Message Filtering
          </h2>
          <p className="text-sm opacity-70 mb-4">Control which messages get processed for TTS</p>
          
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <input 
                type="checkbox"
                id="messageFilteringEnabled"
                className="w-4 h-4 text-blue-600 bg-neutral-800 border-neutral-600 rounded focus:ring-blue-500 focus:ring-2"
                checked={settings.messageFiltering?.enabled ?? true}
                onChange={e => updateSettings({ 
                  messageFiltering: { 
                    ...settings.messageFiltering, 
                    enabled: e.target.checked 
                  } 
                })}
              />
              <label htmlFor="messageFilteringEnabled" className="text-sm font-medium">
                Enable Message Filtering
              </label>
            </div>

            {settings.messageFiltering?.enabled !== false && (
              <div className="space-y-4 pl-7">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-sm font-medium opacity-90">Minimum Length</label>
                    <input 
                      type="number" 
                      min="1" 
                      max="100"
                      className="w-full bg-neutral-800 rounded-lg p-3 text-sm border border-neutral-700 focus:border-blue-500 focus:outline-none"
                      value={settings.messageFiltering?.minLength ?? 1}
                      onChange={e => updateSettings({ 
                        messageFiltering: { 
                          ...settings.messageFiltering, 
                          minLength: parseInt(e.target.value) || 1 
                        } 
                      })}
                    />
                    <p className="text-xs opacity-60">Messages shorter than this will be skipped</p>
                  </div>
                  
                  <div className="space-y-1">
                    <label className="text-sm font-medium opacity-90">Maximum Length</label>
                    <input 
                      type="number" 
                      min="10" 
                      max="2000"
                      className="w-full bg-neutral-800 rounded-lg p-3 text-sm border border-neutral-700 focus:border-blue-500 focus:outline-none"
                      value={settings.messageFiltering?.maxLength ?? 500}
                      onChange={e => updateSettings({ 
                        messageFiltering: { 
                          ...settings.messageFiltering, 
                          maxLength: parseInt(e.target.value) || 500 
                        } 
                      })}
                    />
                    <p className="text-xs opacity-60">Messages longer than this will be truncated</p>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <input 
                      type="checkbox"
                      id="skipCommands"
                      className="w-4 h-4 text-blue-600 bg-neutral-800 border-neutral-600 rounded focus:ring-blue-500 focus:ring-2"
                      checked={settings.messageFiltering?.skipCommands ?? true}
                      onChange={e => updateSettings({ 
                        messageFiltering: { 
                          ...settings.messageFiltering, 
                          skipCommands: e.target.checked 
                        } 
                      })}
                    />
                    <label htmlFor="skipCommands" className="text-sm font-medium">
                      Skip Commands
                    </label>
                  </div>
                  <p className="text-xs opacity-60 pl-7">Skip messages that start with ! or / (bot commands)</p>

                  <div className="flex items-center gap-3">
                    <input 
                      type="checkbox"
                      id="skipEmotes"
                      className="w-4 h-4 text-blue-600 bg-neutral-800 border-neutral-600 rounded focus:ring-blue-500 focus:ring-2"
                      checked={settings.messageFiltering?.skipEmotes ?? false}
                      onChange={e => updateSettings({ 
                        messageFiltering: { 
                          ...settings.messageFiltering, 
                          skipEmotes: e.target.checked 
                        } 
                      })}
                    />
                    <label htmlFor="skipEmotes" className="text-sm font-medium">
                      Skip Emote-Only Messages
                    </label>
                  </div>
                  <p className="text-xs opacity-60 pl-7">Skip messages that contain only emotes (experimental)</p>

                  <div className="flex items-center gap-3">
                    <input 
                      type="checkbox"
                      id="removeUrls"
                      className="w-4 h-4 text-blue-600 bg-neutral-800 border-neutral-600 rounded focus:ring-blue-500 focus:ring-2"
                      checked={settings.messageFiltering?.removeUrls ?? true}
                      onChange={e => updateSettings({ 
                        messageFiltering: { 
                          ...settings.messageFiltering, 
                          removeUrls: e.target.checked 
                        } 
                      })}
                    />
                    <label htmlFor="removeUrls" className="text-sm font-medium">
                      Remove URLs
                    </label>
                  </div>
                  <p className="text-xs opacity-60 pl-7">Remove web links from messages before TTS processing</p>
                </div>

                <div className="space-y-3">
                  <h4 className="text-sm font-medium">Ignored Users</h4>
                  <IgnoredUsersManager 
                    ignoredUsers={settings.messageFiltering?.ignoredUsers || []}
                    onUpdate={(users) => updateSettings({ 
                      messageFiltering: { 
                        ...settings.messageFiltering, 
                        ignoredUsers: users 
                      } 
                    })}
                  />
                  <p className="text-xs opacity-60">Messages from these users will be completely ignored</p>
                </div>

                <div className="p-4 bg-neutral-800 rounded-lg">
                  <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                    <span>🧪</span>
                    Test Message Filter
                  </h4>
                  <MessageFilterTester apiUrl={apiUrl} />
                </div>
              </div>
            )}
          </div>
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
        <div className="text-sm opacity-60 p-4 bg-neutral-800 rounded-lg text-center">
          <span className="text-2xl mb-2 block">🔊</span>
          Activity will appear here when TTS messages are played.
        </div>
      </section>
    </div>
  )
}

function VoiceManager({ managedAvatars, apiUrl }) {
  const [voices, setVoices] = useState([])
  const [availableVoices, setAvailableVoices] = useState({ monstertts: [], google: [], polly: [], edge: [], webspeech: [] })
  const [showAddForm, setShowAddForm] = useState(false)
  const [selectedProvider, setSelectedProvider] = useState('edge')
  const [selectedVoice, setSelectedVoice] = useState('')
  const [loadingMonsterVoices, setLoadingMonsterVoices] = useState(false)
  const [monsterError, setMonsterError] = useState('')

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
      
      // Web Speech API voices (always available, browser-based)
      let webSpeechData = { voices: [] }
      try {
        const webSpeechResponse = await fetch(`${apiUrl}/api/available-voices/webspeech`)
        webSpeechData = await webSpeechResponse.json()
      } catch (error) {
        console.error('Failed to load Web Speech voices:', error)
        // Fallback to common languages
        webSpeechData = {
          voices: [
            {"voice_id": "en-US", "name": "Default US English"},
            {"voice_id": "en-GB", "name": "Default UK English"},
            {"voice_id": "en-CA", "name": "Default Canadian English"}
          ]
        }
      }
      
      setAvailableVoices({
        monstertts: monsterData.voices || [],
        google: googleData.voices || [],
        polly: pollyData.voices || [],
        edge: edgeData.voices || [],
        webspeech: webSpeechData.voices || []
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
      console.log(`Testing voice: ${voiceName} (${provider}, ${voiceId})`)
      
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
        console.log('Voice test message sent successfully')
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
                <option value="webspeech">Web Speech API (Free)</option>
                <option value="monstertts">MonsterTTS (Rated)</option>
                <option value="google">Google Cloud TTS (Rated)</option>
                <option value="polly" disabled>Amazon Polly (Temporarily Disabled)</option>
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
          
          <div className="flex justify-end gap-2">
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
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-neutral-600 disabled:cursor-not-allowed rounded-lg px-4 py-2 text-sm font-medium transition-colors flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 14.142M13 12a1 1 0 11-2 0 1 1 0 012 0z" />
              </svg>
              Test Voice
            </button>
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
              <p>2. Select "MonsterTTS" and configure API key</p>
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
                        voice.provider === 'google' ? 'text-orange-400' :
                        voice.provider === 'polly' ? 'text-purple-400' : 'text-gray-400'
                      }>
                        {voice.provider === 'monstertts' ? '🤖 MonsterTTS' :
                         voice.provider === 'google' ? '🔊 Google TTS' :
                         voice.provider === 'polly' ? '🗣️ Amazon Polly' :
                         `📢 ${voice.provider}`}
                      </span>
                      <span>•</span>
                      <span>{voice.voice_id}</span>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => testVoice(voice.provider, voice.voice_id, voice.name)}
                    className="px-3 py-1 rounded text-xs font-medium bg-blue-600 hover:bg-blue-700 text-white transition-colors flex items-center gap-1"
                    title="Test this voice with 'I am a chat member'"
                  >
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 14.142M13 12a1 1 0 11-2 0 1 1 0 012 0z" />
                    </svg>
                    Test
                  </button>
                  
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
        <input
          type="text"
          placeholder="Username (optional)"
          className="bg-neutral-700 rounded-lg p-2 text-sm border border-neutral-600 focus:border-blue-500 focus:outline-none"
          value={testUsername}
          onChange={e => setTestUsername(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && testFilter()}
        />
        <input
          type="text"
          placeholder="Enter a test message to see if it passes filtering..."
          className="md:col-span-2 bg-neutral-700 rounded-lg p-2 text-sm border border-neutral-600 focus:border-blue-500 focus:outline-none"
          value={testMessage}
          onChange={e => setTestMessage(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && testFilter()}
        />
      </div>
      <button
        onClick={testFilter}
        disabled={testing || !testMessage.trim()}
        className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-neutral-600 disabled:cursor-not-allowed transition-colors rounded-lg px-4 py-2 text-sm font-medium"
      >
        {testing ? 'Testing...' : 'Test Message Filter'}
      </button>
      
      {testResult && (
        <div className={`p-3 rounded-lg text-sm ${
          testResult.success 
            ? testResult.should_process 
              ? 'bg-green-900/30 border border-green-700/50' 
              : 'bg-yellow-900/30 border border-yellow-700/50'
            : 'bg-red-900/30 border border-red-700/50'
        }`}>
          {testResult.success ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-lg">
                  {testResult.should_process ? '✅' : '⚠️'}
                </span>
                <span className="font-medium">
                  {testResult.should_process ? 'Message will be processed' : 'Message will be filtered out'}
                </span>
              </div>
              
              {testResult.test_username && (
                <div className="text-xs opacity-80">
                  <strong>Username:</strong> {testResult.test_username}
                </div>
              )}
              
              {testResult.was_modified && (
                <div className="space-y-1">
                  <p className="text-xs opacity-80">Original: "{testResult.original_message}"</p>
                  <p className="text-xs opacity-80">Filtered: "{testResult.filtered_message}"</p>
                </div>
              )}
              
              <div className="text-xs opacity-70">
                <strong>Current settings:</strong>
                <ul className="mt-1 space-y-0.5 ml-4">
                  <li>• Enabled: {testResult.filtering_settings.enabled ? 'Yes' : 'No'}</li>
                  <li>• Min length: {testResult.filtering_settings.minLength}</li>
                  <li>• Max length: {testResult.filtering_settings.maxLength}</li>
                  <li>• Skip commands: {testResult.filtering_settings.skipCommands ? 'Yes' : 'No'}</li>
                  <li>• Skip emotes: {testResult.filtering_settings.skipEmotes ? 'Yes' : 'No'}</li>
                  <li>• Remove URLs: {testResult.filtering_settings.removeUrls ? 'Yes' : 'No'}</li>
                  <li>• Ignored users: {testResult.filtering_settings.ignoredUsers?.length || 0} users</li>
                </ul>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <span className="text-lg">❌</span>
              <span>Error: {testResult.error}</span>
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
    
    // Check if user is already in the list (case-insensitive)
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
      {/* Add single user */}
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Enter username to ignore..."
          className="flex-1 bg-neutral-700 rounded-lg p-2 text-sm border border-neutral-600 focus:border-blue-500 focus:outline-none"
          value={newUser}
          onChange={e => setNewUser(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && addUser()}
        />
        <button
          onClick={addUser}
          disabled={!newUser.trim()}
          className="bg-blue-600 hover:bg-blue-700 disabled:bg-neutral-600 disabled:cursor-not-allowed transition-colors rounded-lg px-4 py-2 text-sm font-medium"
        >
          Add
        </button>
      </div>

      {/* Current ignored users list */}
      {ignoredUsers.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium opacity-90">
              Ignored Users ({ignoredUsers.length})
            </span>
            <button
              onClick={clearAllUsers}
              className="text-xs text-red-400 hover:text-red-300 underline"
            >
              Clear All
            </button>
          </div>
          
          <div className="max-h-32 overflow-y-auto space-y-1">
            {ignoredUsers.map((user, index) => (
              <div key={index} className="flex items-center justify-between bg-neutral-800 rounded-lg p-2">
                <span className="text-sm font-mono">{user}</span>
                <button
                  onClick={() => removeUser(user)}
                  className="text-red-400 hover:text-red-300 text-xs font-medium"
                  title={`Remove ${user}`}
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {ignoredUsers.length === 0 && (
        <p className="text-xs opacity-60 text-center py-2">
          No users ignored yet
        </p>
      )}
    </div>
  )
}
