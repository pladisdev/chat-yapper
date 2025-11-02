import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import logger from '../utils/logger'
import { hexColorWithOpacity } from '../utils/colorUtils'

// Audio playback constants
const AUDIO_READY_TIMEOUT_MS = 5000 // 5 seconds timeout for audio readiness check
const READY_STATE_HAVE_FUTURE_DATA = 3 // HTMLMediaElement.HAVE_FUTURE_DATA

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
    ? `http://localhost:${import.meta.env.VITE_BACKEND_PORT || 8008}`  // Vite dev server connecting to backend
    : '' // Production or direct backend access (relative URLs)

  // CRITICAL: Load settings FIRST before anything else initializes
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await fetch(`${apiUrl}/api/settings`)
        const settingsData = await response.json()
        
        // Backward compatibility: migrate old popupFixedBottom to new settings
        if (settingsData.popupFixedBottom && !settingsData.popupFixedEdge) {
          settingsData.popupFixedEdge = true
          settingsData.popupDirection = settingsData.popupDirection || 'bottom'
          logger.info('Migrated old popupFixedBottom setting to popupFixedEdge')
        }
        
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
          avatarSize: 60,
          popupDirection: 'bottom',
          popupFixedEdge: false,
          popupRotateToDirection: false
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

  // Track which slots are currently active (still needed for visual feedback in GRID mode)
  const [activeSlots, setActiveSlots] = useState({})
  
  // Pop-up mode: Track independent avatar instances (not tied to slots)
  // Each message creates a new avatar that appears and disappears
  const [popupAvatars, setPopupAvatars] = useState([])
  const popupIdCounter = useRef(0)
  
  // Track chat messages for both grid and popup modes
  const [chatMessages, setChatMessages] = useState({}) // slotId/popupId -> message text
  
  // Helper function to check if two positions overlap
  const checkOverlap = useCallback((pos1, pos2, avatarSize) => {
    // Convert percentage positions to pixel coordinates
    const x1 = (pos1.xPercent * dimensions.width) / 100
    const y1 = (pos1.yPercent * dimensions.height) / 100
    const x2 = (pos2.xPercent * dimensions.width) / 100
    const y2 = (pos2.yPercent * dimensions.height) / 100
    
    // Calculate distance between centers
    const distance = Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2))
    
    // Check if distance is less than the sum of radii (with 10% padding for safety)
    const scaleMultiplier = 1.1
    const effectiveSize = avatarSize * scaleMultiplier
    const minDistance = effectiveSize * 1.1 // 10% padding between avatars
    
    return distance < minDistance
  }, [dimensions.width, dimensions.height])
  
  // Helper function to generate random position with margins based on avatar size
  const generateRandomPosition = useCallback((existingPositions = []) => {
    // CRITICAL: Use settingsRef.current to get the LATEST settings value
    // This avoids stale closure issues where the callback captures old settings
    const currentSettings = settingsRef.current
    const avatarSize = currentSettings?.avatarSize || 60
    const scaleMultiplier = 1.1 // Avatar scales to 110% when active
    const popupDirection = currentSettings?.popupDirection || 'bottom'
    const useFixedEdge = currentSettings?.popupFixedEdge || false
    
    // Debug: Log the settings to see what we're getting
    logger.info('generateRandomPosition called with settings:', {
      popupDirection,
      popupFixedEdge: currentSettings?.popupFixedEdge,
      useFixedEdge,
      settingsLoaded: !!currentSettings,
      existingAvatars: existingPositions.length
    })
    
    // Calculate margin as percentage based on avatar size and viewport dimensions
    // Account for scale animation: use half of scaled size as margin
    const effectiveSize = avatarSize * scaleMultiplier
    const marginXPercent = ((effectiveSize / 2) / dimensions.width) * 100
    const marginYPercent = ((effectiveSize / 2) / dimensions.height) * 100
    
    // Try to find a non-overlapping position
    const maxAttempts = 50 // Try up to 50 times before giving up
    let attempt = 0
    let xPercent, yPercent
    let foundNonOverlapping = false
    
    while (attempt < maxAttempts) {
      if (useFixedEdge) {
        // Fixed edge: position avatar at the edge of the chosen direction
        // The avatar center will be at the edge, making it slightly obscured
        if (popupDirection === 'bottom') {
          // Random X, fixed at bottom edge
          const randomX = Math.random() * 100
          xPercent = marginXPercent + (randomX * (100 - 2 * marginXPercent)) / 100
          yPercent = 100 - ((effectiveSize / 2) / dimensions.height) * 100
        } else if (popupDirection === 'top') {
          // Random X, fixed at top edge
          const randomX = Math.random() * 100
          xPercent = marginXPercent + (randomX * (100 - 2 * marginXPercent)) / 100
          yPercent = ((effectiveSize / 2) / dimensions.height) * 100
        } else if (popupDirection === 'left') {
          // Random Y, fixed at left edge
          const randomY = Math.random() * 100
          xPercent = ((effectiveSize / 2) / dimensions.width) * 100
          yPercent = marginYPercent + (randomY * (100 - 2 * marginYPercent)) / 100
        } else { // right
          // Random Y, fixed at right edge
          const randomY = Math.random() * 100
          xPercent = 100 - ((effectiveSize / 2) / dimensions.width) * 100
          yPercent = marginYPercent + (randomY * (100 - 2 * marginYPercent)) / 100
        }
      } else {
        // Random position within safe bounds
        const randomX = Math.random() * 100
        const randomY = Math.random() * 100
        xPercent = marginXPercent + (randomX * (100 - 2 * marginXPercent)) / 100
        yPercent = marginYPercent + (randomY * (100 - 2 * marginYPercent)) / 100
      }
      
      // Check if this position overlaps with any existing avatars
      const newPos = { xPercent, yPercent }
      const hasOverlap = existingPositions.some(existingPos => 
        checkOverlap(newPos, existingPos, avatarSize)
      )
      
      if (!hasOverlap) {
        foundNonOverlapping = true
        logger.info(`Found non-overlapping position after ${attempt + 1} attempt(s)`)
        break
      }
      
      attempt++
    }
    
    if (!foundNonOverlapping && existingPositions.length > 0) {
      logger.warn(`Could not find non-overlapping position after ${maxAttempts} attempts, using last generated position`)
    }
    
    return { xPercent, yPercent }
  }, [dimensions.width, dimensions.height, checkOverlap]) // Only depend on dimensions since we use settingsRef.current for settings
  
  // Helper function to get random avatar from available avatars
  
  // Helper function to create a new popup avatar instance
  const createPopupAvatar = useCallback((audioElement, avatarData, message) => {
    const id = `popup_${popupIdCounter.current++}`
    
    // Get existing avatar positions to avoid overlaps
    setPopupAvatars(currentAvatars => {
      const existingPositions = currentAvatars.map(a => a.position)
      const position = generateRandomPosition(existingPositions)
      
      // Debug: Log the avatar data structure
      logger.info('Creating popup with avatar data:', {
        name: avatarData?.name,
        isSingleImage: avatarData?.isSingleImage,
        defaultImage: avatarData?.defaultImage,
        speakingImage: avatarData?.speakingImage,
        fullData: avatarData
      })
      
      const popupAvatar = {
        id,
        position,
        avatarData: avatarData, // Use backend-provided avatar data
        isActive: false, // Start inactive, will animate in
        audio: audioElement
      }
      
      // Store the chat message
      if (message) {
        setChatMessages(prev => ({ ...prev, [id]: message }))
      }
      
      // Activate after a brief delay to trigger animation
      setTimeout(() => {
        setPopupAvatars(avatars => 
          avatars.map(a => a.id === id ? {...a, isActive: true} : a)
        )
      }, 50)
      
      logger.info(`Created popup avatar ${id} at position (${Math.round(position.xPercent)}%, ${Math.round(position.yPercent)}%) with avatar "${avatarData?.name || 'unknown'}"`)
      
      return [...currentAvatars, popupAvatar]
    })
    
    return id
  }, [generateRandomPosition])
  
  // Helper function to remove a popup avatar
  const removePopupAvatar = useCallback((id) => {
    // First deactivate to trigger animation
    setPopupAvatars(avatars => 
      avatars.map(a => a.id === id ? {...a, isActive: false} : a)
    )
    
    // Remove after animation completes
    setTimeout(() => {
      setPopupAvatars(avatars => avatars.filter(a => a.id !== id))
      setChatMessages(prev => {
        const newMessages = { ...prev }
        delete newMessages[id]
        return newMessages
      })
      logger.info(`Removed popup avatar ${id}`)
    }, 500) // Match transition duration
  }, [])
  
  // Helper function to activate slot with random position for GRID mode only
  const activateSlot = useCallback((slotId, message) => {
    setActiveSlots(slots => ({...slots, [slotId]: true}))
    if (message) {
      setChatMessages(prev => ({ ...prev, [slotId]: message }))
    }
    logger.info(`Activated slot ${slotId}`)
  }, [])
  
  // Helper function to deactivate slot for GRID mode only
  const deactivateSlot = useCallback((slotId) => {
    setActiveSlots(slots => ({...slots, [slotId]: false}))
    setChatMessages(prev => {
      const newMessages = { ...prev }
      delete newMessages[slotId]
      return newMessages
    })
  }, [])
  
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
          activateSlot(nextSpeech.targetSlot.id, nextSpeech.data.text)
        })
        
        const end = () => {
          logger.info('Web Speech ended - deactivating avatar:', nextSpeech.targetSlot.id)
          deactivateSlot(nextSpeech.targetSlot.id)
          
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
        
        // Configure audio element to prevent crackling and improve playback quality
        audio.preload = 'auto'  // Preload the audio file to avoid playback interruptions
        audio.crossOrigin = 'anonymous'  // Enable CORS for audio processing
        
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
      
      // Check current avatar mode
      const currentAvatarMode = settingsRef.current?.avatarMode || 'grid'
      
      if (!isWebSpeech) {
        if (currentAvatarMode === 'popup') {
          // Pop-up mode: Create a new independent avatar instance
          logger.info('Pop-up mode: Creating new avatar instance')
          
          // Use a ref object so the cleanup can access the latest popupId value
          const popupIdRef = { current: null }
          
          audio.addEventListener('play', () => {
            logger.info('Audio started playing - creating popup avatar')
            popupIdRef.current = createPopupAvatar(audio, selectedAvatar, msg.message)
          })
          
          let cleanedUp = false
          const end = () => {
            if (cleanedUp) return
            cleanedUp = true
            
            logger.info('Audio ended - removing popup avatar')
            if (popupIdRef.current) {
              removePopupAvatar(popupIdRef.current)
            } else {
              logger.warn('Popup avatar was removed before popupId was set')
            }
            
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
            end()
          })
          
        } else if (targetSlot) {
          // Grid mode: Use slot-based system
          logger.info('Grid mode: Setting up avatar animation for slot:', targetSlot.id)
          
          if (selectedAvatar) {
            logger.info(`Using selected avatar "${selectedAvatar.name}" for slot ${targetSlot.id}`)
          }
          
          audio.addEventListener('play', () => {
            logger.info('Audio started playing - activating avatar:', targetSlot.id)
            activateSlot(targetSlot.id, msg.message)
          })
          
          let cleanedUp = false
          const end = () => {
            if (cleanedUp) return
            cleanedUp = true
            
            logger.info('Audio ended - deactivating avatar:', targetSlot.id)
            deactivateSlot(targetSlot.id)
            
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
            notifySlotError(targetSlot.id, e.message || 'Audio playback error')
            end()
          })
        }
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
        
        // Add error handler for loading issues that could cause crackling
        audio.addEventListener('error', (e) => {
          logger.error(`Audio loading error for ${msg.user}:`, e, audio.error)
          // CRITICAL: Clean up on error to prevent backend thinking slot is occupied
          if (targetSlot) {
            notifySlotError(targetSlot.id, audio.error?.message || 'Audio loading error')
          }
        })
        
        // Wait for audio to be ready before playing to prevent crackling from premature playback
        const tryPlay = () => {
          audio.play()
            .then(() => {
              logger.info(`Audio play() successful for ${msg.user} (parallel audio supported) - final volume: ${Math.round(audio.volume * 100)}%`)
            })
            .catch((error) => {
              console.error(`Audio play() failed for ${msg.user}:`, error)
              // CRITICAL: Clean up on play failure to prevent backend thinking slot is occupied
              if (currentAvatarMode === 'popup') {
                // For popup mode, use the cleanup from the earlier event listeners
                // The 'error' event listener will handle cleanup
              } else if (targetSlot) {
                const end = () => {
                  logger.info('Audio ended (from play error) - deactivating avatar:', targetSlot.id)
                  deactivateSlot(targetSlot.id)
                  notifySlotEnded(targetSlot.id)
                  const username = msg.user?.toLowerCase()
                  if (username && activeAudioRef.current.get(username) === audio) {
                    activeAudioRef.current.delete(username)
                  }
                  if (audio) {
                    allActiveAudioRef.current.delete(audio)
                  }
                }
                end()
              }
            })
        }
        
        // Check if audio is ready
        if (audio.readyState >= 3) {
          // HAVE_FUTURE_DATA or better - safe to play
          tryPlay()
        } else {
          // Wait for canplaythrough event to ensure smooth playback
          const canPlayHandler = () => {
            audio.removeEventListener('canplaythrough', canPlayHandler)
            tryPlay()
          }
          audio.addEventListener('canplaythrough', canPlayHandler)
          
          // Fallback timeout in case canplaythrough never fires
          setTimeout(() => {
            if (audio.readyState < READY_STATE_HAVE_FUTURE_DATA) {
              logger.warn(`Audio still not ready after 5s for ${msg.user}, attempting to play anyway`)
              audio.removeEventListener('canplaythrough', canPlayHandler)
              tryPlay()
            }
          }, AUDIO_READY_TIMEOUT_MS)
        }
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
    console.log('YappersPage WebSocket useEffect triggered')
    console.log('settingsLoaded:', settingsLoaded)
    console.log('settings:', settings)
    
    if (!settingsLoaded) {
      logger.info('Waiting for settings to load before WebSocket initialization')
      console.log('Settings not loaded yet, skipping WebSocket init')
      return
    }

    console.log('Settings loaded! Proceeding with WebSocket initialization...')
    
    // Import global WebSocket manager directly
    let removeListener = null
    let mounted = true
    
    // Add a small delay to prevent rapid connect/disconnect in development
    const connectTimeout = setTimeout(() => {
      console.log('YappersPage: Timeout elapsed, checking if still mounted...')
      if (!mounted) {
        console.log('Component unmounted before WebSocket init')
        return
      }

      console.log('YappersPage: Importing WebSocket manager...')
      import('../websocket-manager.js').then(({ default: wsManager }) => {
        if (!mounted) {
          console.log('Component unmounted after import')
          return
        }
        console.log('WebSocket manager imported successfully')
        logger.info('YappersPage: Adding WebSocket listener (settings loaded)')
        console.log('YappersPage: Calling wsManager.addListener()...')
        removeListener = wsManager.addListener(handleMessage)
        console.log('Listener added, removeListener function received')

        // Store WebSocket reference for sending messages
        wsRef.current = wsManager.ws
        
        // Request initial avatar slots when connected
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          console.log('WebSocket already open, requesting avatar slots')
          requestAvatarSlots()
        } else {
          console.log('WebSocket not open yet, will request slots on connect')
          // Wait for connection and then request slots
          const originalOnOpen = wsManager.ws?.onopen
          if (wsManager.ws) {
            wsManager.ws.onopen = (event) => {
              console.log('WebSocket opened via onopen handler')
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
        logger.info('YappersPage: Removing WebSocket listener')
        // Add a small delay before removing to prevent rapid disconnect/reconnect
        setTimeout(() => removeListener(), 50)
      }
    }
  }, [settingsLoaded, handleMessage]) // Wait for settings to load!

  // Show loading state until settings are properly initialized
  if (!settingsLoaded || !settings) {
    return <div className="p-6 font-sans">Loading settings...</div>
  }

  const avatarMode = settings?.avatarMode || 'grid'

  return (
    <div className="min-h-screen bg-transparent p-4">
      {/* Chat bubble fade-in animation */}
      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: scale(0.9); }
          to { opacity: 1; transform: scale(1); }
        }
      `}</style>
      {/* Voice Avatars Overlay */}
      <div className="fixed inset-0 pointer-events-none">
        {/* Debug info */}
        {avatarSlots.length === 0 && (
          <div className="absolute top-4 left-4 bg-black bg-opacity-50 text-white p-2 rounded text-sm pointer-events-auto">
            No avatar slots available. Generation: {assignmentGeneration}
          </div>
        )}
        
        {avatarMode === 'grid' ? (
          // Grid Mode - Original crowd formation
          avatarSlots.map((slot, index) => {
            // Grid layout with individual row configuration
            const baseSize = settings?.avatarSize || 60
            const spacingX = settings?.avatarSpacingX || settings?.avatarSpacing || 50
            const spacingY = settings?.avatarSpacingY || settings?.avatarSpacing || 50
            const baseX = 100 // Starting position from left
            const baseY = 100 // Starting position from bottom
            
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
          // Note: Calculate total rows to invert row positioning (bottom to top)
          const totalRows = Math.max(...avatarSlots.map(s => s.row)) + 1
          const x = baseX + slot.col * spacingX + centerOffset + honeycombOffset
          const y = baseY + (totalRows - 1 - slot.row) * spacingY // Invert row order for bottom-up positioning
          
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
            <div key={slot.id}
              style={{ 
                position: 'absolute',
                left: `${x - baseSize/2}px`,
                bottom: `${y - baseSize/2}px`,
                width: `${baseSize}px`,
                height: `${baseSize}px`,
                transform: activeSlots[slot.id] ? 'translateY(-2.5px)' : 'translateY(0)',
                zIndex: 10 + index,
                transition: 'all 300ms ease-out',
                pointerEvents: 'none'
              }}
            >
              {/* Chat bubble for grid mode */}
              {settings?.chatBubblesEnabled !== false && chatMessages[slot.id] && (
                <div
                  style={{
                    position: 'absolute',
                    left: '50%',
                    top: '-10px',
                    transform: 'translate(-50%, -100%)',
                    minWidth: '120px',
                    maxWidth: '300px',
                    padding: '8px 12px',
                    background: hexColorWithOpacity(settings?.bubbleBackgroundColor || '#000000', settings?.bubbleOpacity ?? 0.85),
                    color: settings?.bubbleFontColor || '#ffffff',
                    borderRadius: (settings?.bubbleRounded ?? true) ? '12px' : '4px',
                    fontFamily: settings?.bubbleFontFamily || 'Arial, sans-serif',
                    fontSize: `${settings?.bubbleFontSize ?? 14}px`,
                    lineHeight: '1.4',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    pointerEvents: 'none',
                    zIndex: 1,
                    opacity: activeSlots[slot.id] ? 1 : 0,
                    transition: 'opacity 300ms ease-out',
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
                  }}
                >
                  {chatMessages[slot.id]}
                  {/* Speech bubble tail */}
                  <div
                    style={{
                      position: 'absolute',
                      bottom: '-6px',
                      left: '50%',
                      transform: 'translateX(-50%)',
                      width: 0,
                      height: 0,
                      borderLeft: '6px solid transparent',
                      borderRight: '6px solid transparent',
                      borderTop: `6px solid ${hexColorWithOpacity(settings?.bubbleBackgroundColor || '#000000', settings?.bubbleOpacity ?? 0.85)}`
                    }}
                  />
                </div>
              )}
              
              {/* Avatar image */}
              <div 
                style={{
                  width: '100%',
                  height: '100%',
                  filter: activeSlots[slot.id] ? activeFilter : inactiveFilter,
                  transition: 'all 300ms ease-out'
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
                        imagePath = `http://localhost:${import.meta.env.VITE_BACKEND_PORT || 8008}${imagePath}`
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
            </div>
          )})
        ) : (
          // Pop-up Mode - Each message creates a new avatar instance
          popupAvatars.map((popupAvatar, index) => {
            const baseSize = settings?.avatarSize || 60
            const scaleMultiplier = 1.1
            const { id, position, avatarData, isActive } = popupAvatar
            const { xPercent, yPercent } = position
            const popupDirection = settings?.popupDirection || 'bottom'
            const rotateToDirection = settings?.popupRotateToDirection || false
            
            // Calculate position to ensure avatar is fully visible
            const xPos = `calc(${xPercent}% - ${baseSize / 2}px)`
            const yPos = `calc(${yPercent}% - ${baseSize / 2}px)`
            
            // Calculate rotation based on direction
            const getRotation = () => {
              if (!rotateToDirection) return 0
              switch (popupDirection) {
                case 'top': return 180
                case 'left': return 90
                case 'right': return -90
                case 'bottom':
                default: return 0
              }
            }
            const rotation = getRotation()
            
            // Calculate complete positioning based on direction
            const getPositioning = () => {
              const hiddenOffset = baseSize + 20
              
              switch (popupDirection) {
                case 'bottom':
                  // yPercent is from top (0-100), but bottom CSS property is from bottom
                  // So we need to invert: if yPercent is 90 (near bottom), bottom should be small (10% from bottom)
                  const bottomPos = `calc(${100 - yPercent}% - ${baseSize / 2}px)`
                  return {
                    staticAxis: { left: xPos },
                    hiddenPos: { bottom: `-${hiddenOffset}px` },
                    visiblePos: { bottom: bottomPos }
                  }
                case 'top':
                  return {
                    staticAxis: { left: xPos },
                    hiddenPos: { top: `-${hiddenOffset}px` },
                    visiblePos: { top: yPos }
                  }
                case 'left':
                  return {
                    staticAxis: { top: yPos },
                    hiddenPos: { left: `-${hiddenOffset}px` },
                    visiblePos: { left: xPos }
                  }
                case 'right':
                  return {
                    staticAxis: { top: yPos },
                    hiddenPos: { right: `-${hiddenOffset}px` },
                    visiblePos: { right: `calc(100% - ${xPos} - ${baseSize}px)` }
                  }
                default:
                  return {
                    staticAxis: { left: xPos },
                    hiddenPos: { bottom: `-${hiddenOffset}px` },
                    visiblePos: { bottom: yPos }
                  }
              }
            }
            const { staticAxis, hiddenPos, visiblePos } = getPositioning()
            
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
            
            // Calculate chat bubble position based on direction
            // Position bubble relative to avatar container, so it moves with the avatar
            const getChatBubbleStyle = () => {
              const bubbleOffset = 10 // Distance from avatar
              const bgColor = settings?.bubbleBackgroundColor || '#000000'
              const opacity = settings?.bubbleOpacity ?? 0.85
              const baseStyle = {
                position: 'absolute',
                minWidth: '120px',
                maxWidth: '300px',
                padding: '8px 12px',
                background: hexColorWithOpacity(bgColor, opacity),
                color: settings?.bubbleFontColor || '#ffffff',
                borderRadius: (settings?.bubbleRounded ?? true) ? '12px' : '4px',
                fontFamily: settings?.bubbleFontFamily || 'Arial, sans-serif',
                fontSize: `${settings?.bubbleFontSize ?? 14}px`,
                lineHeight: '1.4',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                pointerEvents: 'none',
                zIndex: 1,
                opacity: isActive ? 1 : 0,
                transition: 'opacity 300ms ease-out',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
              }
              
              switch (popupDirection) {
                case 'bottom':
                  // Bubble appears above the avatar (centered horizontally)
                  return {
                    ...baseStyle,
                    left: '50%',
                    top: `-${bubbleOffset}px`,
                    transform: 'translate(-50%, -100%)'
                  }
                case 'top':
                  // Bubble appears below the avatar (centered horizontally)
                  return {
                    ...baseStyle,
                    left: '50%',
                    bottom: `-${bubbleOffset}px`,
                    transform: 'translate(-50%, 100%)'
                  }
                case 'left':
                  // Bubble appears to the right of left-entering avatars
                  return {
                    ...baseStyle,
                    left: `${baseSize + bubbleOffset}px`,
                    top: '50%',
                    transform: 'translateY(-50%)'
                  }
                case 'right':
                  // Bubble appears to the left of right-entering avatars
                  return {
                    ...baseStyle,
                    right: `${baseSize + bubbleOffset}px`,
                    top: '50%',
                    transform: 'translateY(-50%)'
                  }
                default:
                  return {
                    ...baseStyle,
                    left: '50%',
                    top: `-${bubbleOffset}px`,
                    transform: 'translate(-50%, -100%)'
                  }
              }
            }
            
            // Calculate chat bubble tail position
            const getChatBubbleTail = () => {
              const bgColor = settings?.bubbleBackgroundColor || '#000000'
              const opacity = settings?.bubbleOpacity ?? 0.85
              const tailColor = hexColorWithOpacity(bgColor, opacity)
              
              switch (popupDirection) {
                case 'bottom':
                  return {
                    bottom: '-6px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    borderLeft: '6px solid transparent',
                    borderRight: '6px solid transparent',
                    borderTop: `6px solid ${tailColor}`
                  }
                case 'top':
                  // Bubble is below avatar, tail points up towards avatar
                  return {
                    top: '-6px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    borderLeft: '6px solid transparent',
                    borderRight: '6px solid transparent',
                    borderBottom: `6px solid ${tailColor}`
                  }
                case 'left':
                  // Tail points left (towards avatar) when bubble is on right
                  return {
                    left: '-6px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    borderTop: '6px solid transparent',
                    borderBottom: '6px solid transparent',
                    borderRight: `6px solid ${tailColor}`
                  }
                case 'right':
                  // Tail points right (towards avatar) when bubble is on left
                  return {
                    right: '-6px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    borderTop: '6px solid transparent',
                    borderBottom: '6px solid transparent',
                    borderLeft: `6px solid ${tailColor}`
                  }
                default:
                  return {
                    bottom: '-6px',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    borderLeft: '6px solid transparent',
                    borderRight: '6px solid transparent',
                    borderTop: `6px solid ${tailColor}`
                  }
              }
            }
            
            return (
              <div key={id}
                  style={{ 
                    position: 'absolute',
                    // Static axis position (doesn't animate)
                    ...staticAxis,
                    // Animated position - switches between hidden and visible
                    ...(isActive ? visiblePos : hiddenPos),
                    width: `${baseSize}px`,
                    height: `${baseSize}px`,
                    zIndex: isActive ? 20 + index : 10 + index,
                    transition: 'all 500ms cubic-bezier(0.34, 1.56, 0.64, 1)',
                    pointerEvents: 'none'
                  }}
                >
                  {/* Chat bubble for popup mode */}
                  {settings?.chatBubblesEnabled !== false && chatMessages[id] && (
                    <div style={getChatBubbleStyle()}>
                      {chatMessages[id]}
                      {/* Speech bubble tail */}
                      <div
                        style={{
                          position: 'absolute',
                          width: 0,
                          height: 0,
                          ...getChatBubbleTail()
                        }}
                      />
                    </div>
                  )}
                  
                  {/* Avatar image - rotated wrapper */}
                  <div 
                    style={{
                      width: '100%',
                      height: '100%',
                      transform: `scale(${isActive ? 1.1 : 0.5}) rotate(${rotation}deg)`,
                      filter: isActive ? activeFilter : inactiveFilter,
                      opacity: isActive ? 1 : 0,
                      transition: 'all 500ms cubic-bezier(0.34, 1.56, 0.64, 1)'
                    }}
                  >
                    <div className="w-full h-full overflow-hidden flex items-center justify-center">
                    <img
                      src={(() => {
                        let imagePath = ''
                        
                        // Handle different avatar data formats
                        if (typeof avatarData === 'string') {
                          // Old format - single image path
                          imagePath = avatarData
                        } else if (avatarData && typeof avatarData === 'object') {
                          // New format - dual image support
                          if (avatarData.isSingleImage) {
                            // Single image avatar - use default image regardless of state
                            imagePath = avatarData.defaultImage
                          } else {
                            // Dual image avatar - switch based on active state
                            imagePath = isActive 
                              ? avatarData.speakingImage 
                              : avatarData.defaultImage
                          }
                        } else {
                          // Fallback
                          imagePath = '/voice_avatars/ava.png'
                        }
                        
                        // Add API URL prefix for development mode if needed
                        if (imagePath && !imagePath.startsWith('http') && !imagePath.startsWith('data:')) {
                          // In development mode, prefix with API URL
                          if (location.hostname === 'localhost' && (location.port === '5173' || location.port === '5174')) {
                            imagePath = `http://localhost:${import.meta.env.VITE_BACKEND_PORT || 8008}${imagePath}`
                          }
                          // In production or direct backend access, relative URLs work fine
                        }
                        
                        return imagePath
                      })()}
                      alt={`Popup Avatar ${index + 1}`}
                      style={{
                        imageRendering: 'auto',
                        width: '100%',
                        height: '100%',
                        objectFit: 'contain'
                      }}
                    />
                    </div>
                  </div>
                </div>
            )
          })
        )}
      </div>
    </div>
  )
}
