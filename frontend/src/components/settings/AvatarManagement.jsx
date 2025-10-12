import React, { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Button } from '../ui/button'
import { Image } from 'lucide-react'
import logger from '../../utils/logger'

function AvatarManagement({
  managedAvatars,
  apiUrl,
  avatarName,
  setAvatarName,
  uploadMode,
  setUploadMode,
  uploading,
  setUploading,
  selectedAvatarGroup,
  setSelectedAvatarGroup,
  lastUploadedName,
  setLastUploadedName,
  allVoices,
  settings,
  setManagedAvatars
}) {
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

export default AvatarManagement