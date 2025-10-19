import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import logger from '../utils/logger'

export default function YappersPage() {
  const [settings, setSettings] = useState(null)
  const [settingsLoaded, setSettingsLoaded] = useState(false)
  const [log, setLog] = useState([])
  const [dimensions, setDimensions] = useState({ width: 1200, height: 800 })
  
  // Use ref to always have the latest settings value without waiting for React re-render
  // This solves timing issues where settings update via WebSocket but audio is created before re-render
  const settingsRef = useRef(null)
  
  // Track active audio objects for stopping
  // Supports parallel audio: multiple users can have TTS playing simultaneously
  // Per-user queuing: if a user sends TTS while their previous TTS is playing, new one is ignored
  const activeAudioRef = useRef(new Map()) // username -> Audio object (one per user)
  const allActiveAudioRef = useRef(new Set()) // All Audio objects for global stop

  // Determine the correct API URL
  const apiUrl = location.hostname === 'localhost' && (location.port === '5173' || location.port === '5174')
    ? 'http://localhost:8000'  // Vite dev server connecting to backend
    : '' // Production or direct backend access (relative URLs)

  // CRITICAL: Load settings FIRST before anything else initializes
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await fetch(`${apiUrl}/api/settings`)
        const settingsData = await response.json()
        setSettings(settingsData)
        settingsRef.current = settingsData  // Keep ref in sync
        setSettingsLoaded(true)
        logger.info('Settings loaded successfully', settingsData)
      } catch (error) {
        logger.error('Failed to load settings:', error)
        // Set default settings to prevent crashes
        const defaultSettings = {
          volume: 1.0,
          avatarRows: 2,
          avatarRowConfig: [6, 6],
          avatarSize: 60
        }
        setSettings(defaultSettings)
        settingsRef.current = defaultSettings  // Keep ref in sync
        setSettingsLoaded(true)
      }
    }
    
    loadSettings()
  }, [apiUrl])
  
  // Keep settingsRef in sync whenever settings state changes
  useEffect(() => {
    if (settings) {
      settingsRef.current = settings
    }
  }, [settings])

  // Update volume for all currently playing audio when volume setting changes
  useEffect(() => {
    if (settings?.volume !== undefined) {
      const volume = settings.volume
      let updatedCount = 0
      let skippedCount = 0
      
      allActiveAudioRef.current.forEach(audio => {
        if (audio && !audio.ended) {
          // Update volume even if paused - this ensures the volume is correct when it resumes
          const oldVolume = audio.volume
          audio.volume = volume
          updatedCount++
          logger.info(`Updated audio volume from ${Math.round(oldVolume * 100)}% to ${Math.round(volume * 100)}%`)
        } else {
          skippedCount++
        }
      })
      
      if (updatedCount > 0 || skippedCount > 0) {
        logger.info(`Volume update complete: ${Math.round(volume * 100)}% applied to ${updatedCount} audio object(s), ${skippedCount} skipped (ended)`)
      }
    }
  }, [settings?.volume])

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const updateDimensions = () => {
        setDimensions({ width: window.innerWidth, height: window.innerHeight })
      }
      updateDimensions()
      window.addEventListener('resize', updateDimensions)
      return () => window.removeEventListener('resize', updateDimensions)
    }
  }, [])

  // Backend-managed avatar slot assignments
  const [avatarSlots, setAvatarSlots] = useState([])
  const [assignmentGeneration, setAssignmentGeneration] = useState(0)
  const wsRef = useRef(null)
  
  // Request avatar slots from backend on component mount
  const requestAvatarSlots = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'request_avatar_slots' }))
      logger.info('Requested avatar slots from backend')
    }
  }, [])
  
  // Notify backend when avatar slot finishes playing
  const notifySlotEnded = useCallback((slotId) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ 
        type: 'avatar_slot_ended', 
        slot_id: slotId 
      }))
      logger.info(`Notified backend that slot ${slotId} ended`)
    }
  }, [])
  
  // Notify backend when avatar slot has an error
  const notifySlotError = useCallback((slotId, error) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ 
        type: 'avatar_slot_error', 
        slot_id: slotId,
        error: error
      }))
      logger.info(`Notified backend that slot ${slotId} had error:`, error)
    }
  }, [])

  // Simple function to re-randomize avatars via backend API
  const reRandomizeAvatars = useCallback(async () => {
    try {
      const response = await fetch(`${apiUrl}/api/avatar-slots/regenerate`, {
        method: 'POST'
      })
      const data = await response.json()
      if (data.success) {
        logger.info('Avatar slots regenerated by backend')
        // The backend will broadcast the update via WebSocket
      } else {
        logger.error('Failed to regenerate avatar slots:', data.error)
      }
    } catch (error) {
      logger.error('Failed to regenerate avatar slots:', error)
    }
  }, [apiUrl])

  // Track which slots are currently active (still needed for visual feedback)
  const [activeSlots, setActiveSlots] = useState({})
  
  // Web Speech API queue management
  const [speechQueue, setSpeechQueue] = useState([])
  const [isSpeaking, setIsSpeaking] = useState(false)

  // Process Web Speech queue
  const processSpeechQueue = useCallback(() => {
    if (isSpeaking || speechQueue.length === 0) return
    
    const nextSpeech = speechQueue[0]
    setIsSpeaking(true)
    
    logger.info('Processing Web Speech from queue:', nextSpeech.data.text)
    
    if ('speechSynthesis' in window) {
      const utterance = new SpeechSynthesisUtterance(nextSpeech.data.text)
      
      // Try to find a voice that matches the requested language
      const voices = speechSynthesis.getVoices()
      const matchingVoice = voices.find(voice => 
        voice.lang.startsWith(nextSpeech.data.voice) || 
        voice.lang === nextSpeech.data.voice.replace('-', '_')
      )
      
      if (matchingVoice) {
        utterance.voice = matchingVoice
        logger.info('Using Web Speech voice:', matchingVoice.name)
      } else {
        logger.info('No matching voice found, using default for:', nextSpeech.data.voice)
      }
      
      // Set up event handlers for avatar animation
      if (nextSpeech.targetSlot) {
        utterance.addEventListener('start', () => {
          logger.info('Web Speech started - activating avatar:', nextSpeech.targetSlot.id)
          setActiveSlots(slots => ({...slots, [nextSpeech.targetSlot.id]: true}))
        })
        
        const end = () => {
          logger.info('Web Speech ended - deactivating avatar:', nextSpeech.targetSlot.id)
          setActiveSlots(slots => ({...slots, [nextSpeech.targetSlot.id]: false}))
          
          // Remove completed speech from queue and process next
          setSpeechQueue(queue => queue.slice(1))
          setIsSpeaking(false)
        }
        
        utterance.addEventListener('end', end)
        utterance.addEventListener('error', (e) => {
          console.error('Web Speech error:', e)
          end()
        })
      } else {
        const end = () => {
          logger.info('Web Speech ended (no avatar)')
          setSpeechQueue(queue => queue.slice(1))
          setIsSpeaking(false)
        }
        
        utterance.addEventListener('end', end)
        utterance.addEventListener('error', (e) => {
          console.error('Web Speech error:', e)
          end()
        })
      }
      
      // Speak the text
      speechSynthesis.speak(utterance)
      logger.info('Web Speech utterance started from queue')
    } else {
      console.error('Web Speech API not supported in this browser')
      // Remove from queue and continue
      setSpeechQueue(queue => queue.slice(1))
      setIsSpeaking(false)
    }
  }, [isSpeaking, speechQueue])
  
  // Process queue when it changes or speaking status changes
  useEffect(() => {
    processSpeechQueue()
  }, [processSpeechQueue])

  // Stable message handler that doesn't change on every render
  const handleMessage = useCallback((msg) => {
    logger.info('Processing message:', msg)
    
    // Debug: Log all message types for debugging
    if (msg.type === 'settings_updated') {
      logger.info('SETTINGS_UPDATED message received in YappersPage!')
    }
    
    // Handle TTS cancellation for specific user
    if (msg.type === 'tts_cancelled' && msg.stop_audio) {
      logger.info('Stopping TTS for user:', msg.user)
      const userAudio = activeAudioRef.current.get(msg.user?.toLowerCase())
      if (userAudio) {
        userAudio.pause()
        userAudio.currentTime = 0
        activeAudioRef.current.delete(msg.user?.toLowerCase())
        allActiveAudioRef.current.delete(userAudio)
        logger.info('Stopped audio for user:', msg.user)
      }
      
      // Web Speech API limitation: Can't stop individual users, must stop all
      // Regular audio files support per-user stopping, but Web Speech API is global
      if ('speechSynthesis' in window && speechSynthesis.speaking) {
        speechSynthesis.cancel()
        setSpeechQueue([])
        logger.info('Cancelled Web Speech synthesis (all users - API limitation)')
      }
      return
    }
    
    // Handle moderation events (ban/timeout) with immediate audio stop
    if (msg.type === 'moderation' && msg.stop_user_audio) {
      logger.info('Moderation event - stopping TTS for user:', msg.stop_user_audio)
      const userAudio = activeAudioRef.current.get(msg.stop_user_audio?.toLowerCase())
      if (userAudio) {
        userAudio.pause()
        userAudio.currentTime = 0
        activeAudioRef.current.delete(msg.stop_user_audio?.toLowerCase())
        allActiveAudioRef.current.delete(userAudio)
        logger.info('Stopped audio for moderated user:', msg.stop_user_audio)
      }
      
      // Web Speech API limitation: Can't stop individual users, must stop all
      // Regular audio files support per-user stopping, but Web Speech API is global
      if ('speechSynthesis' in window && speechSynthesis.speaking) {
        speechSynthesis.cancel()
        setSpeechQueue([])
        logger.info('Cancelled Web Speech synthesis due to moderation (all users - API limitation)')
      }
      
      // Add moderation event to log
      setLog(l => [{
        t: new Date().toLocaleTimeString(),
        user: msg.stop_user_audio,
        text: `[${msg.eventType.toUpperCase()}] ${msg.message}`,
        voice: null,
        eventType: msg.eventType
      }, ...l].slice(0, 50))
      
      // Continue processing other aspects of the moderation event
      // (don't return here so other moderation logic can run if needed)
    }
    
    // Handle global TTS stop
    if (msg.type === 'tts_global_stopped' && msg.stop_all_audio) {
      logger.info('Stopping all TTS audio')
      // Stop all audio objects
      allActiveAudioRef.current.forEach(audio => {
        try {
          audio.pause()
          audio.currentTime = 0
        } catch (e) {
          logger.warn('Failed to stop audio:', e)
        }
      })
      // Stop Web Speech API
      if ('speechSynthesis' in window) {
        speechSynthesis.cancel()
        logger.info('Cancelled Web Speech synthesis')
      }
      // Clear speech queue
      setSpeechQueue([])
      // Clear all tracking
      activeAudioRef.current.clear()
      allActiveAudioRef.current.clear()
      // Clear active slots
      setActiveSlots({})
      logger.info('All TTS audio stopped')
      return
    }
    
    // Handle settings update (reload settings without full page refresh)
    if (msg.type === 'settings_updated') {
      logger.info('Settings updated, refetching from backend...', msg)
      
      // Always fetch from backend - backend is the source of truth
      fetch(`${apiUrl}/api/settings`)
        .then(r => r.json())
        .then(data => {
          const oldRows = settings?.avatarRows
          const oldRowConfig = settings?.avatarRowConfig
          const oldSize = settings?.avatarSize
          const oldVolume = settings?.volume
          const newRows = data?.avatarRows
          const newRowConfig = data?.avatarRowConfig
          const newSize = data?.avatarSize
          const newVolume = data?.volume
          
          // Check if any display-affecting settings changed
          const layoutChanged = oldRows !== newRows || JSON.stringify(oldRowConfig) !== JSON.stringify(newRowConfig)
          const sizeChanged = oldSize !== newSize
          const volumeChanged = oldVolume !== newVolume
          
          if (volumeChanged) {
            logger.info(`Volume changed: ${Math.round((oldVolume || 1.0) * 100)}% -> ${Math.round((newVolume || 1.0) * 100)}%`)
          }
          
          if (layoutChanged) {
            localStorage.removeItem('chatyapper_avatar_assignments')
            logger.info('Avatar layout changed, cleared saved assignments')
          }
          
          if (layoutChanged || sizeChanged) {
            logger.info('Display settings changed - avatar slots will be regenerated by backend')
          }
          
          // Apply settings
          setSettings(data)
          settingsRef.current = data  // Keep ref in sync
          logger.info('Settings reloaded from backend')
        })
        .catch(error => {
          logger.error('Failed to refetch settings:', error)
        })
      return
    }
    
    // Handle avatar update - backend now manages slots automatically
    if (msg.type === 'refresh' || msg.type === 'avatar_updated') {
      logger.info('Avatars updated - backend will regenerate slots automatically')
      // Backend already handles avatar changes and will broadcast avatar_slots_updated
      return
    }
    
    // Handle avatar slots update from backend
    if (msg.type === 'avatar_slots_updated') {
      logger.info('Received updated avatar slots from backend:', msg.slots?.length || 0, 'slots')
      if (msg.slots) {
        // Log the first few slots for debugging
        if (msg.slots.length > 0) {
          logger.info('Sample avatar slot data:', {
            id: msg.slots[0].id,
            avatarName: msg.slots[0].avatarData?.name,
            defaultImage: msg.slots[0].avatarData?.defaultImage,
            speakingImage: msg.slots[0].avatarData?.speakingImage
          })
        }
        setAvatarSlots(msg.slots)
        setAssignmentGeneration(msg.generationId || msg.assignmentGeneration || 0)
        logger.info('Avatar slots updated (generation #' + (msg.generationId || msg.assignmentGeneration || 0) + ')')
      }
      return
    }
    
    // Handle avatar re-randomization
    if (msg.type === 're_randomize_avatars') {
      logger.info('Re-randomizing avatar assignments...')
      reRandomizeAvatars()
      return
    }
    
    if (msg.type === 'play') {
      logger.info('▶Playing TTS:', msg.audioUrl)
      
      // Check if this is a Web Speech API file (client-side TTS)
      const isWebSpeech = msg.audioUrl.includes('_webspeech.json')
      
      // Use backend-provided slot information
      const targetSlot = msg.targetSlot
      const selectedAvatar = msg.avatarData
      
      if (targetSlot) {
        logger.info(`Backend assigned slot ${targetSlot.id} with avatar "${selectedAvatar?.name || 'unknown'}"`)
      } else {
        logger.info('No slot assigned by backend - TTS will play without avatar animation')
      }
      
      let audio = null
      if (!isWebSpeech) {
        audio = new Audio(msg.audioUrl)
        
        // Set volume from settings (0.0 to 1.0)
        // Use settingsRef to get the LATEST value immediately, avoiding React state update delays
        const currentSettings = settingsRef.current || settings
        const volumeToSet = currentSettings?.volume !== undefined ? currentSettings.volume : 1.0
        audio.volume = volumeToSet
        logger.info(`Created new Audio with volume: ${Math.round(volumeToSet * 100)}% (from settingsRef: ${Math.round((currentSettings?.volume || 1.0) * 100)}%)`, msg.audioUrl)
        
        // Track this audio object for potential cancellation
        const username = msg.user?.toLowerCase()
        if (username) {
          // Clean up any finished audio for this user
          const existingAudio = activeAudioRef.current.get(username)
          if (existingAudio && (existingAudio.ended || existingAudio.paused)) {
            logger.info(`🧹 Cleaning up finished audio for user: ${username}`)
            allActiveAudioRef.current.delete(existingAudio)
          }
          
          // Track new audio for this user (backend already handled per-user queuing logic)
          activeAudioRef.current.set(username, audio)
          allActiveAudioRef.current.add(audio)
          logger.info(`Now tracking audio for user: ${username} (Total active: ${allActiveAudioRef.current.size})`)
        }
      }
      
      if (targetSlot && !isWebSpeech) {
        logger.info('Setting up avatar animation for slot:', targetSlot.id)
        
        // Note: targetSlot already has the correct avatarData assigned
        // If we selected a specific avatar, it should match what's in the slot
        if (selectedAvatar) {
          logger.info(`Using selected avatar "${selectedAvatar.name}" for slot ${targetSlot.id}`)
        }
        
        audio.addEventListener('play', () => {
          logger.info('Audio started playing - activating avatar:', targetSlot.id)
          setActiveSlots(slots => ({...slots, [targetSlot.id]: true}))
        })
        
        let cleanedUp = false // Flag to prevent duplicate cleanup
        const end = () => {
          if (cleanedUp) return // Prevent duplicate calls
          cleanedUp = true
          
          logger.info('Audio ended - deactivating avatar:', targetSlot.id)
          setActiveSlots(slots => ({...slots, [targetSlot.id]: false}))
          
          // Notify backend that slot has ended
          notifySlotEnded(targetSlot.id)
          
          // Clean up audio tracking
          const username = msg.user?.toLowerCase()
          if (username && activeAudioRef.current.get(username) === audio) {
            activeAudioRef.current.delete(username)
          }
          if (audio) {
            allActiveAudioRef.current.delete(audio)
          }
        }
        audio.addEventListener('ended', end)
        audio.addEventListener('pause', end)
        audio.addEventListener('error', (e) => {
          console.error('Audio error:', e)
          // Notify backend of slot error
          notifySlotError(targetSlot.id, e.message || 'Audio playback error')
          end() // Clean up on error
        })
      }
      
      if (isWebSpeech) {
        // Handle Web Speech API with queue
        logger.info('Using Web Speech API - checking user availability...')
        
        // Backend already handled per-user queuing logic - just add to Web Speech queue
        logger.info('Adding message to Web Speech queue (backend already validated per-user queuing)...')
        
        // Note: targetSlot already has the correct avatarData assigned
        if (selectedAvatar && targetSlot) {
          logger.info(`Using selected avatar "${selectedAvatar.name}" for slot ${targetSlot.id}`)
        }
        
        // Fetch the JSON instructions
        fetch(msg.audioUrl)
          .then(response => response.json())
          .then(data => {
            logger.info('Web Speech instructions:', data)
            
            // Add user information to the data for queue management
            const dataWithUser = { ...data, user: msg.user }
            
            // Add to speech queue instead of playing immediately
            setSpeechQueue(queue => [...queue, { data: dataWithUser, targetSlot }])
            logger.info(`Web Speech added to queue for user: ${msg.user}`)
          })
          .catch(error => {
            console.error('Failed to load Web Speech instructions:', error)
            // CRITICAL: Clean up on fetch failure to prevent backend thinking slot is occupied
            end()
          })
      } else {
        // Handle regular audio file
        logger.info(`Attempting to play audio for ${msg.user}... (${allActiveAudioRef.current.size} total active)`)
        logger.info(`Audio volume just before play: ${Math.round(audio.volume * 100)}%`)
        audio.play()
          .then(() => {
            logger.info(`Audio play() successful for ${msg.user} (parallel audio supported) - final volume: ${Math.round(audio.volume * 100)}%`)
          })
          .catch((error) => {
            console.error(`Audio play() failed for ${msg.user}:`, error)
            // CRITICAL: Clean up on play failure to prevent backend thinking slot is occupied
            end()
          })
      }
      
      setLog(l => [{
        t: new Date().toLocaleTimeString(),
        user: msg.user,
        text: msg.message,
        voice: msg.voice?.id,
        eventType: msg.eventType
      }, ...l].slice(0, 50))
    }
  }, [apiUrl, reRandomizeAvatars]) // Dependencies for WebSocket message handling

  // CRITICAL: Only initialize WebSocket AFTER settings are loaded
  useEffect(() => {
    if (!settingsLoaded) {
      logger.info('Waiting for settings to load before WebSocket initialization')
      return
    }

    // Import global WebSocket manager directly
    let removeListener = null
    let mounted = true
    
    // Add a small delay to prevent rapid connect/disconnect in development
    const connectTimeout = setTimeout(() => {
      if (!mounted) return
      
      import('../websocket-manager.js').then(({ default: wsManager }) => {
        if (!mounted) return
        logger.info('YappersPage: Adding WebSocket listener (settings loaded)')
        removeListener = wsManager.addListener(handleMessage)
        
        // Store WebSocket reference for sending messages
        wsRef.current = wsManager.ws
        
        // Request initial avatar slots when connected
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          requestAvatarSlots()
        } else {
          // Wait for connection and then request slots
          const originalOnOpen = wsManager.ws?.onopen
          if (wsManager.ws) {
            wsManager.ws.onopen = (event) => {
              if (originalOnOpen) originalOnOpen(event)
              wsRef.current = wsManager.ws
              requestAvatarSlots()
            }
          }
        }
      })
    }, 100) // Small delay to debounce rapid re-mounts
    
    return () => {
      mounted = false
      clearTimeout(connectTimeout)
      
      if (removeListener) {
        logger.info('🔌 YappersPage: Removing WebSocket listener')
        // Add a small delay before removing to prevent rapid disconnect/reconnect
        setTimeout(() => removeListener(), 50)
      }
    }
  }, [settingsLoaded, handleMessage]) // Wait for settings to load!

  // Show loading state until settings are properly initialized
  if (!settingsLoaded || !settings) {
    return <div className="p-6 font-sans">Loading settings...</div>
  }

  return (
    <div className="min-h-screen bg-transparent p-4">
      {/* Voice Avatars Overlay - Crowd Formation */}
      <div className="fixed inset-0 pointer-events-none">
        {/* Debug info */}
        {avatarSlots.length === 0 && (
          <div className="absolute top-4 left-4 bg-black bg-opacity-50 text-white p-2 rounded text-sm pointer-events-auto">
            No avatar slots available. Generation: {assignmentGeneration}
          </div>
        )}
        
        {avatarSlots.map((slot, index) => {
          // Grid layout with individual row configuration
          const baseSize = settings?.avatarSize || 60
          const spacingX = settings?.avatarSpacingX || settings?.avatarSpacing || 50
          const spacingY = settings?.avatarSpacingY || settings?.avatarSpacing || 50
          const baseX = 100 // Starting position from left
          const baseY = 100 // Starting position from top
          
          // Calculate centering offset for this row
          const maxAvatarsInAnyRow = Math.max(...(settings?.avatarRowConfig || [6, 6]))
          const avatarsInThisRow = slot.totalInRow
          const maxRowWidth = (maxAvatarsInAnyRow - 1) * spacingX
          const thisRowWidth = (avatarsInThisRow - 1) * spacingX
          const centerOffset = (maxRowWidth - thisRowWidth) / 2 // Center shorter rows
          
          // Add honeycomb offset - create true honeycomb/brick pattern
          // For proper honeycomb: alternate between offset and no offset, with shorter rows getting preference for offset
          const isMaxWidthRow = avatarsInThisRow === maxAvatarsInAnyRow
          const shouldOffset = isMaxWidthRow ? (slot.row % 2 === 1) : (slot.row % 2 === 0) // Alternate pattern, but flip for shorter rows
          const honeycombOffset = shouldOffset ? spacingX / 2 : 0 // Offset by half spacing for honeycomb pattern
          
          // Calculate position based on row and column with centering and honeycomb offset
          const x = baseX + slot.col * spacingX + centerOffset + honeycombOffset
          const y = baseY + slot.row * spacingY
          
          // Get glow effect settings
          const glowEnabled = settings?.avatarGlowEnabled ?? true
          const glowColor = settings?.avatarGlowColor ?? '#ffffff'
          const glowOpacity = settings?.avatarGlowOpacity ?? 0.9
          const glowSize = settings?.avatarGlowSize ?? 20
          
          // Convert hex color to rgba for glow effect
          const hexToRgba = (hex, opacity) => {
            const r = parseInt(hex.slice(1, 3), 16)
            const g = parseInt(hex.slice(3, 5), 16)
            const b = parseInt(hex.slice(5, 7), 16)
            return `rgba(${r},${g},${b},${opacity})`
          }
          
          // Build filter based on glow settings
          const activeFilter = glowEnabled
            ? `brightness(1.25) drop-shadow(0 0 ${glowSize}px ${hexToRgba(glowColor, glowOpacity)})`
            : 'brightness(1.25)'
          const inactiveFilter = 'drop-shadow(0 4px 8px rgba(0,0,0,0.3))'
          
          return (
            <div 
              key={slot.id}
              style={{ 
                position: 'absolute',
                left: `${x - baseSize/2}px`,
                top: `${y - baseSize/2}px`,
                width: `${baseSize}px`,
                height: `${baseSize}px`,
                transform: activeSlots[slot.id] ? 'translateY(-2.5px)' : 'translateY(0)',
                filter: activeSlots[slot.id] ? activeFilter : inactiveFilter,
                zIndex: 10 + index,
                transition: 'all 300ms ease-out',
                pointerEvents: 'none'
              }}
            >
              <div className="w-full h-full overflow-hidden flex items-center justify-center">
                <img
                  src={(() => {
                    let imagePath = ''
                    
                    // Handle different avatar data formats
                    if (typeof slot.avatarData === 'string') {
                      // Old format - single image path
                      imagePath = slot.avatarData
                    } else if (slot.avatarData && typeof slot.avatarData === 'object') {
                      // New format - dual image support
                      if (slot.avatarData.isSingleImage) {
                        // Single image avatar - use default image regardless of state
                        imagePath = slot.avatarData.defaultImage
                      } else {
                        // Dual image avatar - switch based on active state
                        imagePath = activeSlots[slot.id] 
                          ? slot.avatarData.speakingImage 
                          : slot.avatarData.defaultImage
                      }
                    } else {
                      // Fallback
                      imagePath = '/voice_avatars/ava.png'
                    }
                    
                    // Add API URL prefix for development mode if needed
                    if (imagePath && !imagePath.startsWith('http') && !imagePath.startsWith('data:')) {
                      // In development mode, prefix with API URL
                      if (location.hostname === 'localhost' && (location.port === '5173' || location.port === '5174')) {
                        imagePath = `http://localhost:8000${imagePath}`
                      }
                      // In production or direct backend access, relative URLs work fine
                    }
                    
                    // Debug: log the final image path for the first slot to verify URL construction
                    if (index === 0 && imagePath) {
                      console.debug(`🖼️ Loading avatar image: ${imagePath}`)
                    }
                    
                    return imagePath
                  })()}
                  alt={`Avatar ${index + 1}`}
                  style={{
                    imageRendering: 'auto',
                    width: '100%',
                    height: '100%',
                    objectFit: 'contain'
                  }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
