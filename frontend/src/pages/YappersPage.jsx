import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'

export default function YappersPage() {
  const [settings, setSettings] = useState(null)
  const [log, setLog] = useState([])
  const [dimensions, setDimensions] = useState({ width: 1200, height: 800 })

  // Determine the correct API URL
  const apiUrl = location.hostname === 'localhost' && (location.port === '5173' || location.port === '5174')
    ? 'http://localhost:8000'  // Vite dev server connecting to backend
    : '' // Production or direct backend access (relative URLs)

  useEffect(() => {
    fetch(`${apiUrl}/api/settings`).then(r => r.json()).then(setSettings)
  }, [apiUrl])

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
          // Group managed avatars by name/group
          const grouped = {}
          managedData.avatars.forEach(avatar => {
            const key = avatar.avatar_group_id || `single_${avatar.id}`
            if (!grouped[key]) grouped[key] = { name: avatar.name, images: {} }
            grouped[key].images[avatar.avatar_type] = avatar.file_path
          })
          
          // Convert to avatar objects
          const avatarGroups = Object.values(grouped).map(group => ({
            name: group.name,
            defaultImage: group.images.default || group.images.speaking, // Fallback to speaking if no default
            speakingImage: group.images.speaking || group.images.default, // Fallback to default if no speaking
            isSingleImage: !group.images.speaking || !group.images.default || group.images.speaking === group.images.default
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
  
  // Generate avatar slots based on individual row configuration
  const avatarSlots = useMemo(() => {
    if (availableAvatars.length === 0) return [] // Wait for avatars to load
    
    const avatarRows = settings?.avatarRows || 2
    const avatarRowConfig = settings?.avatarRowConfig || [6, 6]
    const slots = []
    let slotIndex = 0
    
    for (let rowIndex = 0; rowIndex < avatarRows; rowIndex++) {
      const avatarsInThisRow = avatarRowConfig[rowIndex] || 6
      
      for (let colIndex = 0; colIndex < avatarsInThisRow; colIndex++) {
        // Assign avatar data, cycling through available avatars
        const avatarData = availableAvatars[slotIndex % availableAvatars.length]
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
  }, [settings?.avatarRows, settings?.avatarRowConfig, availableAvatars])
  
  // Track which slots are currently active
  const [activeSlots, setActiveSlots] = useState({})
  
  // Web Speech API queue management
  const [speechQueue, setSpeechQueue] = useState([])
  const [isSpeaking, setIsSpeaking] = useState(false)

  // Use refs to avoid useCallback dependencies changing constantly
  const avatarSlotsRef = useRef([])
  const activeSlotsRef = useRef({})
  
  // Keep refs updated
  useEffect(() => {
    avatarSlotsRef.current = avatarSlots
  }, [avatarSlots])
  
  useEffect(() => {
    activeSlotsRef.current = activeSlots
  }, [activeSlots])

  // Process Web Speech queue
  const processSpeechQueue = useCallback(() => {
    if (isSpeaking || speechQueue.length === 0) return
    
    const nextSpeech = speechQueue[0]
    setIsSpeaking(true)
    
    console.log('🗣️ Processing Web Speech from queue:', nextSpeech.data.text)
    
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
        console.log('🔊 Using Web Speech voice:', matchingVoice.name)
      } else {
        console.log('⚠️ No matching voice found, using default for:', nextSpeech.data.voice)
      }
      
      // Set up event handlers for avatar animation
      if (nextSpeech.targetSlot) {
        utterance.addEventListener('start', () => {
          console.log('🟢 Web Speech started - activating avatar:', nextSpeech.targetSlot.id)
          setActiveSlots(slots => ({...slots, [nextSpeech.targetSlot.id]: true}))
        })
        
        const end = () => {
          console.log('🔴 Web Speech ended - deactivating avatar:', nextSpeech.targetSlot.id)
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
          console.log('🔴 Web Speech ended (no avatar)')
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
      console.log('✅ Web Speech utterance started from queue')
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
    console.log('🎵 Processing message:', msg)
    if (msg.type === 'play') {
      console.log('▶️ Playing TTS:', msg.audioUrl)
      
      const currentSlots = avatarSlotsRef.current
      const currentActiveSlots = activeSlotsRef.current
      
      console.log('🎭 Available avatar slots:', currentSlots.length)
      console.log('🎭 Active slots:', currentActiveSlots)
      
      const voiceId = msg.voice?.id || msg.voice?.name || 'unknown'
      
      // Check if this is a Web Speech API file (client-side TTS)
      const isWebSpeech = msg.audioUrl.includes('_webspeech.json')
      
      let audio = null
      if (!isWebSpeech) {
        audio = new Audio(msg.audioUrl)
      }
      
      // Find next available slot or use random slot
      let targetSlot = null
      if (currentSlots.length > 0) {
        const availableSlots = currentSlots.filter(slot => !currentActiveSlots[slot.id])
        console.log('🎯 Available slots for animation:', availableSlots.length)
        
        if (availableSlots.length > 0) {
          targetSlot = availableSlots[Math.floor(Math.random() * availableSlots.length)]
        } else {
          // All slots are active, pick a random one to override
          targetSlot = currentSlots[Math.floor(Math.random() * currentSlots.length)]
        }
        
        console.log('🎯 Selected slot for animation:', targetSlot?.id)
      }
      
      if (targetSlot && !isWebSpeech) {
        console.log('🎬 Setting up avatar animation for slot:', targetSlot.id)
        audio.addEventListener('play', () => {
          console.log('🟢 Audio started playing - activating avatar:', targetSlot.id)
          setActiveSlots(slots => ({...slots, [targetSlot.id]: true}))
        })
        
        const end = () => {
          console.log('🔴 Audio ended - deactivating avatar:', targetSlot.id)
          setActiveSlots(slots => ({...slots, [targetSlot.id]: false}))
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
        console.log('🗣️ Using Web Speech API - adding to queue...')
        
        // Fetch the JSON instructions
        fetch(msg.audioUrl)
          .then(response => response.json())
          .then(data => {
            console.log('📋 Web Speech instructions:', data)
            
            // Add to speech queue instead of playing immediately
            setSpeechQueue(queue => [...queue, { data, targetSlot }])
            console.log('✅ Web Speech added to queue')
          })
          .catch(error => {
            console.error('❌ Failed to load Web Speech instructions:', error)
          })
      } else {
        // Handle regular audio file
        console.log('🔊 Attempting to play audio...')
        audio.play()
          .then(() => {
            console.log('✅ Audio play() successful')
          })
          .catch((error) => {
            console.error('❌ Audio play() failed:', error)
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
  }, []) // No dependencies - stable callback

  useEffect(() => {
    // Import global WebSocket manager directly
    let removeListener = null
    
    import('../websocket-manager.js').then(({ default: wsManager }) => {
      console.log('🔌 YappersPage: Adding WebSocket listener')
      removeListener = wsManager.addListener(handleMessage)
    })
    
    return () => {
      if (removeListener) {
        console.log('🔌 YappersPage: Removing WebSocket listener')
        removeListener()
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
          
          // Add honeycomb offset for even rows (2nd, 4th, 6th, etc.)
          const isEvenRow = (slot.row + 1) % 2 === 0 // +1 because rows are 0-indexed
          const honeycombOffset = isEvenRow ? spacingX / 2 : 0 // Offset even rows by half horizontal spacing
          
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
