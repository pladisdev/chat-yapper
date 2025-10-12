import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import logger from '../utils/logger'

export default function YappersPage() {
  const [settings, setSettings] = useState(null)
  const [log, setLog] = useState([])
  const [dimensions, setDimensions] = useState({ width: 1200, height: 800 })
  
  // Track active audio objects for stopping
  // Supports parallel audio: multiple users can have TTS playing simultaneously
  // Per-user queuing: if a user sends TTS while their previous TTS is playing, new one is ignored
  const activeAudioRef = useRef(new Map()) // username -> Audio object (one per user)
  const allActiveAudioRef = useRef(new Set()) // All Audio objects for global stop

  // Determine the correct API URL
  const apiUrl = location.hostname === 'localhost' && (location.port === '5173' || location.port === '5174')
    ? 'http://localhost:8000'  // Vite dev server connecting to backend
    : '' // Production or direct backend access (relative URLs)

  useEffect(() => {
    fetch(`${apiUrl}/api/settings`).then(r => r.json()).then(setSettings)
  }, [apiUrl])

  // Update volume for all currently playing audio when volume setting changes
  useEffect(() => {
    if (settings?.volume !== undefined) {
      const volume = settings.volume
      allActiveAudioRef.current.forEach(audio => {
        if (audio && !audio.ended && !audio.paused) {
          audio.volume = volume
        }
      })
      logger.info(`🔊 Updated volume to ${Math.round(volume * 100)}% for ${allActiveAudioRef.current.size} active audio(s)`)
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

  // State for dynamically loaded avatar images
  const [availableAvatars, setAvailableAvatars] = useState([])
  
  // Load available avatar images from backend API
  useEffect(() => {
    const loadAvatarImages = async () => {
      const currentApiUrl = location.hostname === 'localhost' && (location.port === '5173' || location.port === '5174')
        ? 'http://localhost:8000'  // Vite dev server connecting to backend
        : '' // Production or direct backend access (relative URLs)
      
      try {
        // Try to load managed avatars first
        const managedResponse = await fetch(`${currentApiUrl}/api/avatars/managed`)
        const managedData = await managedResponse.json()
        
        if (managedData.avatars && managedData.avatars.length > 0) {
          // Group managed avatars by name/group (exclude disabled avatars)
          const grouped = {}
          managedData.avatars
            .filter(avatar => !avatar.disabled) // Exclude disabled avatars from selection pool
            .forEach(avatar => {
            const key = avatar.avatar_group_id || `single_${avatar.id}`
            if (!grouped[key]) {
              grouped[key] = { 
                name: avatar.name, 
                images: {},
                spawn_position: avatar.spawn_position,
                voice_id: avatar.voice_id
              }
            } else {
              // Update spawn_position and voice_id if not null (prefer non-null values)
              if (avatar.spawn_position != null) {
                grouped[key].spawn_position = avatar.spawn_position
              }
              if (avatar.voice_id != null) {
                grouped[key].voice_id = avatar.voice_id
              }
            }
            // Prepend API URL for development environment
            const imagePath = avatar.file_path.startsWith('http') 
              ? avatar.file_path 
              : `${currentApiUrl}${avatar.file_path}`
            grouped[key].images[avatar.avatar_type] = imagePath
          })
          
          logger.info('🔍 Loaded managed avatars:', Object.values(grouped).map(g => ({
            name: g.name,
            voice_id: g.voice_id,
            spawn_position: g.spawn_position
          })))
          
          // Convert to avatar objects
          const avatarGroups = Object.values(grouped).map(group => ({
            name: group.name,
            defaultImage: group.images.default || group.images.speaking, // Fallback to speaking if no default
            speakingImage: group.images.speaking || group.images.default, // Fallback to default if no speaking
            isSingleImage: !group.images.speaking || !group.images.default || group.images.speaking === group.images.default,
            spawn_position: group.spawn_position, // null = random, number = specific slot
            voice_id: group.voice_id // null = random voice
          }))
          
          setAvailableAvatars(avatarGroups)
        } else {
          // Fallback to old avatar system
          const response = await fetch(`${currentApiUrl}/api/avatars`)
          const data = await response.json()
          
          if (data.avatars && data.avatars.length > 0) {
            // Convert old format to new format
            const oldAvatars = data.avatars.map((path, index) => ({
              name: `Avatar ${index + 1}`,
              defaultImage: path,
              speakingImage: path,
              isSingleImage: true
            }))
            setAvailableAvatars(oldAvatars)
          } else {
            // Final fallback to default avatars
            const defaultAvatars = ['/voice_avatars/ava.png', '/voice_avatars/liam.png', '/voice_avatars/3.png'].map((path, index) => ({
              name: `Default ${index + 1}`,
              defaultImage: path,
              speakingImage: path,
              isSingleImage: true
            }))
            setAvailableAvatars(defaultAvatars)
          }
        }
      } catch (error) {
        console.error('Failed to load avatar images:', error)
        // Fallback to default avatars on error
        const defaultAvatars = ['/voice_avatars/ava.png', '/voice_avatars/liam.png', '/voice_avatars/3.png'].map((path, index) => ({
          name: `Default ${index + 1}`,
          defaultImage: path,
          speakingImage: path,
          isSingleImage: true
        }))
        setAvailableAvatars(defaultAvatars)
      }
    }
    
    loadAvatarImages()
  }, [])
  
  // State to store available voices for assignment
  const [enabledVoices, setEnabledVoices] = useState([])
  
  // Load enabled voices
  useEffect(() => {
    const loadVoices = async () => {
      try {
        const response = await fetch(`${apiUrl}/api/voices`)
        const data = await response.json()
        const enabled = data.voices?.filter(v => v.enabled) || []
        setEnabledVoices(enabled)
        logger.info('🎤 Loaded enabled voices:', enabled.map(v => `${v.name} (ID: ${v.id})`))
      } catch (error) {
        console.error('Failed to load voices:', error)
        setEnabledVoices([])
      }
    }
    loadVoices()
  }, [apiUrl])

  // Function to create randomized avatar assignment with voice assignments
  const createRandomizedAvatarAssignment = useCallback((avatars, totalSlots) => {
    if (avatars.length === 0) return []
    
    logger.info('🎲 Creating randomized assignments for', totalSlots, 'slots with', avatars.length, 'avatars')
    logger.info('🎤 Available voices for assignment:', enabledVoices.length === 0 ? 'None (avatars will display without TTS functionality)' : enabledVoices.map(v => `${v.name} (ID: ${v.id})`))
    
    const assignments = []
    
    // First, ensure each avatar appears at least once (if we have enough slots)
    if (totalSlots >= avatars.length) {
      // Add one of each avatar first
      for (let i = 0; i < avatars.length; i++) {
        assignments.push({...avatars[i]}) // Create a copy
      }
      
      // Fill remaining slots with random avatars
      const remainingSlots = totalSlots - avatars.length
      for (let i = 0; i < remainingSlots; i++) {
        const randomAvatar = avatars[Math.floor(Math.random() * avatars.length)]
        assignments.push({...randomAvatar}) // Create a copy
      }
    } else {
      // If we have fewer slots than avatars, just randomly select
      for (let i = 0; i < totalSlots; i++) {
        const randomAvatar = avatars[Math.floor(Math.random() * avatars.length)]
        assignments.push({...randomAvatar}) // Create a copy
      }
    }
    
    // Shuffle the assignments for true randomization
    for (let i = assignments.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1))
      ;[assignments[i], assignments[j]] = [assignments[j], assignments[i]]
    }
    
    logger.info('✅ Final assignments:', assignments.map((a, i) => `Slot ${i}: ${a.name}`))
    
    return assignments
  }, [])

  // State to store randomized avatar assignments
  const [avatarAssignments, setAvatarAssignments] = useState([])

  // Save assignments to localStorage whenever they change
  const saveAvatarAssignments = useCallback((assignments, layoutSettings) => {
    try {
      const assignmentData = {
        assignments: assignments.map(avatar => ({
          name: avatar.name,
          defaultImage: avatar.defaultImage,
          speakingImage: avatar.speakingImage,
          isSingleImage: avatar.isSingleImage,
          voice_id: avatar.voice_id,
          spawn_position: avatar.spawn_position
        })),
        timestamp: Date.now(),
        avatarCount: availableAvatars.length,
        avatarNames: availableAvatars.map(a => a.name).sort(), // For validation
        // Include layout settings for validation
        avatarRows: layoutSettings?.avatarRows || 2,
        avatarRowConfig: layoutSettings?.avatarRowConfig || [6, 6],
        // Include voice configuration for validation
        enabledVoiceIds: enabledVoices.map(v => v.id).sort()
      }
      localStorage.setItem('chatyapper_avatar_assignments', JSON.stringify(assignmentData))
      logger.info('💾 Avatar assignments saved to localStorage:', assignments.map(a => `${a.name} (voice_id: ${a.voice_id})`))
    } catch (error) {
      console.error('❌ Failed to save avatar assignments:', error)
    }
  }, [availableAvatars, enabledVoices])

  // Load assignments from localStorage
  const loadAvatarAssignments = useCallback((layoutSettings) => {
    try {
      const saved = localStorage.getItem('chatyapper_avatar_assignments')
      if (!saved) return null

      const assignmentData = JSON.parse(saved)
      
      // Validate that the saved assignments match current avatars
      const currentAvatarNames = availableAvatars.map(a => a.name).sort()
      const savedAvatarNames = assignmentData.avatarNames || []
      
      // Check if avatar configuration has changed
      if (assignmentData.avatarCount !== availableAvatars.length || 
          JSON.stringify(currentAvatarNames) !== JSON.stringify(savedAvatarNames)) {
        logger.info('🔄 Avatar configuration changed, clearing saved assignments')
        localStorage.removeItem('chatyapper_avatar_assignments')
        return null
      }

      // Check if layout configuration has changed
      const currentRows = layoutSettings?.avatarRows || 2
      const currentRowConfig = layoutSettings?.avatarRowConfig || [6, 6]
      
      if (assignmentData.avatarRows !== currentRows || 
          JSON.stringify(assignmentData.avatarRowConfig) !== JSON.stringify(currentRowConfig)) {
        logger.info('🔄 Layout configuration changed, clearing saved assignments')
        localStorage.removeItem('chatyapper_avatar_assignments')
        return null
      }

      // Check if voice configuration has changed (only if voices are available)
      const currentVoiceIds = enabledVoices.map(v => v.id).sort()
      const savedVoiceIds = assignmentData.enabledVoiceIds || []
      
      // Only validate voice configuration if we have voices
      if (enabledVoices.length > 0 || savedVoiceIds.length > 0) {
        if (JSON.stringify(currentVoiceIds) !== JSON.stringify(savedVoiceIds)) {
          logger.info('🔄 Voice configuration changed, clearing saved assignments')
          localStorage.removeItem('chatyapper_avatar_assignments')
          return null
        }
      }

      logger.info('📂 Loaded avatar assignments from localStorage:', assignmentData.assignments.map(a => `${a.name} (voice_id: ${a.voice_id})`))
      return assignmentData.assignments
    } catch (error) {
      console.error('❌ Failed to load avatar assignments:', error)
      localStorage.removeItem('chatyapper_avatar_assignments')
      return null
    }
  }, [availableAvatars, enabledVoices])

  // Load assignments when avatars, voices, or settings change
  useEffect(() => {
    if (availableAvatars.length === 0 || !settings) return // Wait for avatars and settings to load (voices optional)
    
    // Try to load from localStorage first
    const savedAssignments = loadAvatarAssignments(settings)
    if (savedAssignments) {
      setAvatarAssignments(savedAssignments)
    } else {
      // Clear assignments to trigger regeneration
      setAvatarAssignments([])
    }
  }, [availableAvatars, enabledVoices, settings?.avatarRows, settings?.avatarRowConfig, loadAvatarAssignments])

  // Generate avatar slots based on individual row configuration
  const avatarSlots = useMemo(() => {
    if (availableAvatars.length === 0 || !settings) return [] // Wait for avatars and settings to load (voices optional)
    
    const avatarRows = settings.avatarRows || 2
    const avatarRowConfig = settings.avatarRowConfig || [6, 6]
    const totalSlots = avatarRowConfig.slice(0, avatarRows).reduce((sum, count) => sum + count, 0)
    
    // Create or use existing randomized assignments
    let assignments = avatarAssignments
    if (assignments.length === 0 || assignments.length !== totalSlots) {
      assignments = createRandomizedAvatarAssignment(availableAvatars, totalSlots)
      setAvatarAssignments(assignments)
      // Save the new assignments to localStorage
      saveAvatarAssignments(assignments, settings)
    }
    
    const slots = []
    let slotIndex = 0
    
    for (let rowIndex = 0; rowIndex < avatarRows; rowIndex++) {
      const avatarsInThisRow = avatarRowConfig[rowIndex] || 6
      
      for (let colIndex = 0; colIndex < avatarsInThisRow; colIndex++) {
        // Use randomized assignment instead of cycling
        const avatarData = assignments[slotIndex] || availableAvatars[0] // Fallback to first avatar
        slots.push({
          id: `slot_${slotIndex}`,
          avatarData: avatarData, // Store full avatar data instead of just image path
          isActive: false,
          row: rowIndex,
          col: colIndex,
          totalInRow: avatarsInThisRow
        })
        slotIndex++
      }
    }
    
    return slots
  }, [settings, availableAvatars, avatarAssignments, createRandomizedAvatarAssignment, saveAvatarAssignments])
  
  // Send avatar configuration to backend whenever slots change

  
  // Function to manually re-randomize avatar assignments
  const reRandomizeAvatars = useCallback(() => {
    if (availableAvatars.length === 0 || !settings) return
    
    const avatarRows = settings.avatarRows || 2
    const avatarRowConfig = settings.avatarRowConfig || [6, 6]
    const totalSlots = avatarRowConfig.slice(0, avatarRows).reduce((sum, count) => sum + count, 0)
    
    const newAssignments = createRandomizedAvatarAssignment(availableAvatars, totalSlots)
    setAvatarAssignments(newAssignments)
    saveAvatarAssignments(newAssignments, settings)
    logger.info('🎲 Avatars re-randomized!', newAssignments.map(a => a.name))
  }, [availableAvatars, settings, createRandomizedAvatarAssignment, saveAvatarAssignments])

  // Track which slots are currently active
  const [activeSlots, setActiveSlots] = useState({})
  
  // Web Speech API queue management
  const [speechQueue, setSpeechQueue] = useState([])
  const [isSpeaking, setIsSpeaking] = useState(false)

  // Use refs to avoid useCallback dependencies changing constantly
  const avatarSlotsRef = useRef([])
  const activeSlotsRef = useRef({})
  const availableAvatarsRef = useRef([])
  
  // Keep refs updated
  useEffect(() => {
    avatarSlotsRef.current = avatarSlots
  }, [avatarSlots])
  
  useEffect(() => {
    activeSlotsRef.current = activeSlots
  }, [activeSlots])
  
  useEffect(() => {
    availableAvatarsRef.current = availableAvatars
  }, [availableAvatars])

  // Process Web Speech queue
  const processSpeechQueue = useCallback(() => {
    if (isSpeaking || speechQueue.length === 0) return
    
    const nextSpeech = speechQueue[0]
    setIsSpeaking(true)
    
    logger.info('🗣️ Processing Web Speech from queue:', nextSpeech.data.text)
    
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
        logger.info('🔊 Using Web Speech voice:', matchingVoice.name)
      } else {
        logger.info('⚠️ No matching voice found, using default for:', nextSpeech.data.voice)
      }
      
      // Set up event handlers for avatar animation
      if (nextSpeech.targetSlot) {
        utterance.addEventListener('start', () => {
          logger.info('🟢 Web Speech started - activating avatar:', nextSpeech.targetSlot.id)
          setActiveSlots(slots => ({...slots, [nextSpeech.targetSlot.id]: true}))
        })
        
        const end = () => {
          logger.info('🔴 Web Speech ended - deactivating avatar:', nextSpeech.targetSlot.id)
          setActiveSlots(slots => ({...slots, [nextSpeech.targetSlot.id]: false}))
          
          // Remove completed speech from queue and process next
          setSpeechQueue(queue => queue.slice(1))
          setIsSpeaking(false)
        }
        
        utterance.addEventListener('end', end)
        utterance.addEventListener('error', (e) => {
          console.error('❌ Web Speech error:', e)
          end()
        })
      } else {
        const end = () => {
          logger.info('🔴 Web Speech ended (no avatar)')
          setSpeechQueue(queue => queue.slice(1))
          setIsSpeaking(false)
        }
        
        utterance.addEventListener('end', end)
        utterance.addEventListener('error', (e) => {
          console.error('❌ Web Speech error:', e)
          end()
        })
      }
      
      // Speak the text
      speechSynthesis.speak(utterance)
      logger.info('✅ Web Speech utterance started from queue')
    } else {
      console.error('❌ Web Speech API not supported in this browser')
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
    logger.info('🎵 Processing message:', msg)
    
    // Handle TTS cancellation for specific user
    if (msg.type === 'tts_cancelled' && msg.stop_audio) {
      logger.info('🛑 Stopping TTS for user:', msg.user)
      const userAudio = activeAudioRef.current.get(msg.user?.toLowerCase())
      if (userAudio) {
        userAudio.pause()
        userAudio.currentTime = 0
        activeAudioRef.current.delete(msg.user?.toLowerCase())
        allActiveAudioRef.current.delete(userAudio)
        logger.info('✅ Stopped audio for user:', msg.user)
      }
      
      // Web Speech API limitation: Can't stop individual users, must stop all
      // Regular audio files support per-user stopping, but Web Speech API is global
      if ('speechSynthesis' in window && speechSynthesis.speaking) {
        speechSynthesis.cancel()
        setSpeechQueue([])
        logger.info('🛑 Cancelled Web Speech synthesis (all users - API limitation)')
      }
      return
    }
    
    // Handle moderation events (ban/timeout) with immediate audio stop
    if (msg.type === 'moderation' && msg.stop_user_audio) {
      logger.info('🔨 Moderation event - stopping TTS for user:', msg.stop_user_audio)
      const userAudio = activeAudioRef.current.get(msg.stop_user_audio?.toLowerCase())
      if (userAudio) {
        userAudio.pause()
        userAudio.currentTime = 0
        activeAudioRef.current.delete(msg.stop_user_audio?.toLowerCase())
        allActiveAudioRef.current.delete(userAudio)
        logger.info('✅ Stopped audio for moderated user:', msg.stop_user_audio)
      }
      
      // Web Speech API limitation: Can't stop individual users, must stop all
      // Regular audio files support per-user stopping, but Web Speech API is global
      if ('speechSynthesis' in window && speechSynthesis.speaking) {
        speechSynthesis.cancel()
        setSpeechQueue([])
        logger.info('🛑 Cancelled Web Speech synthesis due to moderation (all users - API limitation)')
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
      logger.info('🛑 Stopping all TTS audio')
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
        logger.info('🛑 Cancelled Web Speech synthesis')
      }
      // Clear speech queue
      setSpeechQueue([])
      // Clear all tracking
      activeAudioRef.current.clear()
      allActiveAudioRef.current.clear()
      // Clear active slots
      setActiveSlots({})
      logger.info('✅ All TTS audio stopped')
      return
    }
    
    // Handle settings update (reload settings without full page refresh)
    if (msg.type === 'settings_updated') {
      logger.info('⚙️ Settings updated, reloading settings and avatars...')
      // Reload settings
      fetch(`${apiUrl}/api/settings`).then(r => r.json()).then(data => {
        const oldRows = settings?.avatarRows
        const oldRowConfig = settings?.avatarRowConfig
        const newRows = data?.avatarRows
        const newRowConfig = data?.avatarRowConfig
        
        // Clear saved assignments if layout configuration changed
        if (oldRows !== newRows || JSON.stringify(oldRowConfig) !== JSON.stringify(newRowConfig)) {
          localStorage.removeItem('chatyapper_avatar_assignments')
          logger.info('🔄 Avatar layout changed, cleared saved assignments')
        }
        
        setSettings(data)
        logger.info('✅ Settings reloaded')
      })
      return
    }
    
    // Handle avatar update (reload avatars only)
    if (msg.type === 'refresh' || msg.type === 'avatar_updated') {
      logger.info('🔄 Avatars updated, reloading avatars...')
      // Reload avatars without full page refresh
      fetch(`${apiUrl}/api/avatars/managed`).then(r => r.json()).then(data => {
        if (data.avatars && data.avatars.length > 0) {
          const grouped = {}
          data.avatars
            .filter(avatar => !avatar.disabled) // Exclude disabled avatars from selection pool
            .forEach(avatar => {
            const key = avatar.avatar_group_id || `single_${avatar.id}`
            if (!grouped[key]) {
              grouped[key] = { 
                name: avatar.name, 
                images: {},
                spawn_position: avatar.spawn_position,
                voice_id: avatar.voice_id
              }
            } else {
              if (avatar.spawn_position != null) {
                grouped[key].spawn_position = avatar.spawn_position
              }
              if (avatar.voice_id != null) {
                grouped[key].voice_id = avatar.voice_id
              }
            }
            const imagePath = avatar.file_path.startsWith('http') 
              ? avatar.file_path 
              : `${apiUrl}${avatar.file_path}`
            grouped[key].images[avatar.avatar_type] = imagePath
          })
          
          const avatarGroups = Object.values(grouped).map(group => ({
            name: group.name,
            defaultImage: group.images.default || group.images.speaking,
            speakingImage: group.images.speaking || group.images.default,
            isSingleImage: !group.images.speaking || !group.images.default || group.images.speaking === group.images.default,
            spawn_position: group.spawn_position,
            voice_id: group.voice_id
          }))
          
          setAvailableAvatars(avatarGroups)
          // Clear saved assignments since avatar configuration changed
          localStorage.removeItem('chatyapper_avatar_assignments')
          logger.info('✅ Avatars reloaded, cleared saved assignments')
        }
      })
      return
    }
    
    // Handle avatar re-randomization
    if (msg.type === 're_randomize_avatars') {
      logger.info('🎲 Re-randomizing avatar assignments...')
      reRandomizeAvatars()
      return
    }
    
    if (msg.type === 'play') {
      logger.info('▶️ Playing TTS:', msg.audioUrl)
      
      const currentSlots = avatarSlotsRef.current
      const currentActiveSlots = activeSlotsRef.current
      
      logger.info('🎭 Available avatar slots:', currentSlots.length)
      logger.info('🎭 Active slots:', currentActiveSlots)
      
      const voiceId = msg.voice?.id || msg.voice?.name || 'unknown'
      
      // Check if this is a Web Speech API file (client-side TTS)
      const isWebSpeech = msg.audioUrl.includes('_webspeech.json')
      
      let audio = null
      if (!isWebSpeech) {
        audio = new Audio(msg.audioUrl)
        
        // Set volume from settings (0.0 to 1.0)
        audio.volume = settings.volume !== undefined ? settings.volume : 1.0
        
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
          logger.info(`🎵 Now tracking audio for user: ${username} (Total active: ${allActiveAudioRef.current.size})`)
        }
      }
      
      // Find next available slot - prefer inactive slots but allow active ones
      let targetSlot = null
      let selectedAvatar = null
      if (currentSlots.length > 0) {
        const availableSlots = currentSlots.filter(slot => !currentActiveSlots[slot.id])
        logger.info('🎯 Available (inactive) slots for animation:', availableSlots.length)
        
        if (availableSlots.length > 0) {
          // Prefer inactive slots for cleaner visual experience
          targetSlot = availableSlots[Math.floor(Math.random() * availableSlots.length)]
          logger.info('🎯 Selected inactive slot')
        } else {
          // All slots are active - that's fine, just pick random slot
          targetSlot = currentSlots[Math.floor(Math.random() * currentSlots.length)]
          logger.info('🎯 All slots active - selected random slot')
        }
        
        // Use the avatar assigned to the selected slot
        if (targetSlot) {
          selectedAvatar = targetSlot.avatarData
          logger.info(`🎯 Using slot ${targetSlot.id} with avatar "${selectedAvatar.name}"`)
        }
      }
      
      if (targetSlot && !isWebSpeech) {
        logger.info('🎬 Setting up avatar animation for slot:', targetSlot.id)
        
        // Note: targetSlot already has the correct avatarData assigned
        // If we selected a specific avatar, it should match what's in the slot
        if (selectedAvatar) {
          logger.info(`🎭 Using selected avatar "${selectedAvatar.name}" for slot ${targetSlot.id}`)
        }
        
        audio.addEventListener('play', () => {
          logger.info('🟢 Audio started playing - activating avatar:', targetSlot.id)
          setActiveSlots(slots => ({...slots, [targetSlot.id]: true}))
        })
        
        let cleanedUp = false // Flag to prevent duplicate cleanup
        const end = () => {
          if (cleanedUp) return // Prevent duplicate calls
          cleanedUp = true
          
          logger.info('🔴 Audio ended - deactivating avatar:', targetSlot.id)
          setActiveSlots(slots => ({...slots, [targetSlot.id]: false}))
          
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
          console.error('❌ Audio error:', e)
          end() // Clean up on error
        })
      }
      
      if (isWebSpeech) {
        // Handle Web Speech API with queue
        logger.info('🗣️ Using Web Speech API - checking user availability...')
        
        // Backend already handled per-user queuing logic - just add to Web Speech queue
        logger.info('🗣️ Adding message to Web Speech queue (backend already validated per-user queuing)...')
        
        // Note: targetSlot already has the correct avatarData assigned
        if (selectedAvatar && targetSlot) {
          logger.info(`🎭 Using selected avatar "${selectedAvatar.name}" for slot ${targetSlot.id}`)
        }
        
        // Fetch the JSON instructions
        fetch(msg.audioUrl)
          .then(response => response.json())
          .then(data => {
            logger.info('📋 Web Speech instructions:', data)
            
            // Add user information to the data for queue management
            const dataWithUser = { ...data, user: msg.user }
            
            // Add to speech queue instead of playing immediately
            setSpeechQueue(queue => [...queue, { data: dataWithUser, targetSlot }])
            logger.info(`✅ Web Speech added to queue for user: ${msg.user}`)
          })
          .catch(error => {
            console.error('❌ Failed to load Web Speech instructions:', error)
            // CRITICAL: Clean up on fetch failure to prevent backend thinking slot is occupied
            end()
          })
      } else {
        // Handle regular audio file
        logger.info(`🔊 Attempting to play audio for ${msg.user}... (${allActiveAudioRef.current.size} total active)`)
        audio.play()
          .then(() => {
            logger.info(`✅ Audio play() successful for ${msg.user} (parallel audio supported)`)
          })
          .catch((error) => {
            console.error(`❌ Audio play() failed for ${msg.user}:`, error)
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

  useEffect(() => {
    // Import global WebSocket manager directly
    let removeListener = null
    let mounted = true
    
    // Add a small delay to prevent rapid connect/disconnect in development
    const connectTimeout = setTimeout(() => {
      if (!mounted) return
      
      import('../websocket-manager.js').then(({ default: wsManager }) => {
        if (!mounted) return
        logger.info('🔌 YappersPage: Adding WebSocket listener')
        removeListener = wsManager.addListener(handleMessage)
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
  }, [handleMessage])

  if (!settings) return <div className="p-6 font-sans">Loading…</div>

  return (
    <div className="min-h-screen bg-transparent p-4">
      {/* Voice Avatars Overlay - Crowd Formation */}
      <div className="fixed inset-0 pointer-events-none">
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
                filter: activeSlots[slot.id] ? 'brightness(1.25) drop-shadow(0 0 20px rgba(255,255,255,0.9))' : 'drop-shadow(0 4px 8px rgba(0,0,0,0.3))',
                zIndex: 10 + index,
                transition: 'all 300ms ease-out',
                pointerEvents: 'none'
              }}
            >
              <div className="w-full h-full rounded-full overflow-hidden flex items-center justify-center">
                <img
                  src={(() => {
                    // Handle different avatar data formats
                    if (typeof slot.avatarData === 'string') {
                      // Old format - single image path
                      return slot.avatarData
                    } else if (slot.avatarData && typeof slot.avatarData === 'object') {
                      // New format - dual image support
                      if (slot.avatarData.isSingleImage) {
                        // Single image avatar - use default image regardless of state
                        return slot.avatarData.defaultImage
                      } else {
                        // Dual image avatar - switch based on active state
                        return activeSlots[slot.id] 
                          ? slot.avatarData.speakingImage 
                          : slot.avatarData.defaultImage
                      }
                    } else {
                      // Fallback
                      return '/voice_avatars/ava.png'
                    }
                  })()}
                  alt={`Avatar ${index + 1}`}
                  style={{
                    imageRendering: 'auto',
                    maxWidth: `${Math.floor((baseSize - 8) * 1.5)}px`,
                    maxHeight: `${Math.floor((baseSize - 8) * 1.5)}px`,
                    width: 'auto',
                    height: 'auto',
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
