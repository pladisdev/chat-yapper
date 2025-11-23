import React, { useState, useEffect, useCallback, useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { LayoutGrid, Plus, Trash2, Save, ChevronUp, ChevronDown } from 'lucide-react'
import logger from '../../utils/logger'

function AvatarLayoutEditor({ apiUrl, managedAvatars }) {
  const [configuredSlots, setConfiguredSlots] = useState([])
  const [selectedSlot, setSelectedSlot] = useState(null)
  const [selectedSlots, setSelectedSlots] = useState([]) // Multi-selection
  const [dimensions] = useState({ width: 800, height: 600 })
  const [isDragging, setIsDragging] = useState(false)
  const [draggedSlot, setDraggedSlot] = useState(null)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const [copiedSlot, setCopiedSlot] = useState(null)
  const [voices, setVoices] = useState([])
  const canvasRef = useRef(null)
  const sizeUpdateTimeoutRef = useRef(null)
  const pendingSizeUpdateRef = useRef(null)
  const draggedListItemRef = useRef(null)
  const dragOverIndexRef = useRef(null)
  
  // Box selection state
  const [isBoxSelecting, setIsBoxSelecting] = useState(false)
  const [boxSelectStart, setBoxSelectStart] = useState({ x: 0, y: 0 })
  const [boxSelectEnd, setBoxSelectEnd] = useState({ x: 0, y: 0 })
  
  // Track if we should clear multi-selection on mouse up (when clicking already-selected item without modifier)
  const [pendingClearMultiSelect, setPendingClearMultiSelect] = useState(false)

  // Load configured slots and voices on mount
  useEffect(() => {
    loadConfiguredSlots()
    loadVoices()
  }, [apiUrl])

  // Keyboard shortcuts for copy/paste/delete
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Only handle shortcuts when not typing in an input field
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') {
        return
      }

      // Ctrl+C or Cmd+C - Copy selected slot(s)
      if ((e.ctrlKey || e.metaKey) && e.key === 'c' && (selectedSlot || selectedSlots.length > 0)) {
        e.preventDefault()
        if (selectedSlots.length > 0) {
          setCopiedSlot({ multiple: true, slots: selectedSlots })
          logger.info(`Copied ${selectedSlots.length} slots`)
        } else if (selectedSlot) {
          setCopiedSlot(selectedSlot)
          logger.info(`Copied slot #${selectedSlot.slot_index + 1}`)
        }
      }

      // Ctrl+V or Cmd+V - Paste copied slot(s)
      if ((e.ctrlKey || e.metaKey) && e.key === 'v' && copiedSlot) {
        e.preventDefault()
        handlePasteSlot()
      }

      // Delete key - Delete selected slot(s)
      if (e.key === 'Delete') {
        e.preventDefault()
        if (selectedSlots.length > 0) {
          handleDeleteMultipleSlots()
        } else if (selectedSlot) {
          handleDeleteSlot(selectedSlot.id)
        }
      }

      // Escape key - Clear selection
      if (e.key === 'Escape') {
        setSelectedSlot(null)
        setSelectedSlots([])
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedSlot, selectedSlots, copiedSlot])

  // Handle wheel events for size adjustment during drag (with passive: false to allow preventDefault)
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const handleWheel = (e) => {
      // Only adjust size when dragging an avatar
      if (!isDragging || !draggedSlot) return
      
      e.preventDefault()
      
      // Determine size change (positive = zoom in, negative = zoom out)
      const delta = e.deltaY < 0 ? 5 : -5
      const currentSize = draggedSlot.size
      const newSize = Math.max(20, Math.min(1000, currentSize + delta))
      
      if (newSize !== currentSize) {
        // Update the dragged slot's size immediately in state for visual feedback
        setDraggedSlot(prev => ({ ...prev, size: newSize }))
        setConfiguredSlots(prev => prev.map(slot => 
          slot.id === draggedSlot.id 
            ? { ...slot, size: newSize }
            : slot
        ))
        
        // Update selected slot if it's the dragged one
        if (selectedSlot?.id === draggedSlot.id) {
          setSelectedSlot(prev => ({ ...prev, size: newSize }))
        }
        
        // Store the pending update but don't save yet
        pendingSizeUpdateRef.current = { slotId: draggedSlot.id, size: newSize }
        
        // Clear existing timeout and set a new one
        if (sizeUpdateTimeoutRef.current) {
          clearTimeout(sizeUpdateTimeoutRef.current)
        }
        
        // Save to backend after user stops scrolling for 500ms
        sizeUpdateTimeoutRef.current = setTimeout(async () => {
          if (pendingSizeUpdateRef.current) {
            await handleUpdateSlot(pendingSizeUpdateRef.current.slotId, { 
              size: pendingSizeUpdateRef.current.size 
            })
            pendingSizeUpdateRef.current = null
          }
        }, 500)
      }
    }

    canvas.addEventListener('wheel', handleWheel, { passive: false })
    return () => {
      canvas.removeEventListener('wheel', handleWheel)
      if (sizeUpdateTimeoutRef.current) {
        clearTimeout(sizeUpdateTimeoutRef.current)
      }
    }
  }, [isDragging, draggedSlot, selectedSlot])

  const loadConfiguredSlots = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/avatar-slots/configured`)
      const data = await response.json()
      if (data.success) {
        setConfiguredSlots(data.slots || [])
        logger.info(`Loaded ${data.slots?.length || 0} configured avatar slots`)
        return data.slots || []
      }
      return []
    } catch (error) {
      logger.error('Failed to load configured avatar slots:', error)
      return []
    }
  }

  const loadVoices = async () => {
    try {
      const response = await fetch(`${apiUrl}/api/voices`)
      const data = await response.json()
      if (data.voices) {
        setVoices(data.voices || [])
        logger.info(`Loaded ${data.voices?.length || 0} voices`)
      }
    } catch (error) {
      logger.error('Failed to load voices:', error)
    }
  }

  // Group managed avatars by group_id
  const groupedAvatars = React.useMemo(() => {
    const grouped = {}
    managedAvatars.forEach(avatar => {
      const key = avatar.avatar_group_id || `single_${avatar.id}`
      if (!grouped[key]) {
        grouped[key] = {
          id: key,
          name: avatar.name,
          images: {},
          disabled: avatar.disabled
        }
      }
      grouped[key].images[avatar.avatar_type] = avatar.file_path
    })
    
    return Object.values(grouped).map(group => ({
      id: group.id,
      name: group.name,
      defaultImage: group.images.default || group.images.speaking,
      speakingImage: group.images.speaking || group.images.default,
      disabled: group.disabled
    }))
  }, [managedAvatars])

  const handleAddSlot = async () => {
    try {
      // Find next available slot index
      const maxIndex = configuredSlots.reduce((max, slot) => Math.max(max, slot.slot_index), -1)
      const newIndex = maxIndex + 1
      
      // Place new slot in center with default size of 100px
      const response = await fetch(`${apiUrl}/api/avatar-slots/configured`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          slot_index: newIndex,
          x_position: 50,
          y_position: 50,
          size: 100,
          avatar_group_id: null
        })
      })
      
      const data = await response.json()
      if (data.success) {
        await loadConfiguredSlots()
        logger.info('Added new avatar slot')
      }
    } catch (error) {
      logger.error('Failed to add avatar slot:', error)
    }
  }

  const handleDeleteSlot = async (slotId) => {
    try {
      const response = await fetch(`${apiUrl}/api/avatar-slots/configured/${slotId}`, {
        method: 'DELETE'
      })
      
      const data = await response.json()
      if (data.success) {
        await loadConfiguredSlots()
        if (selectedSlot?.id === slotId) {
          setSelectedSlot(null)
        }
        // Remove from multi-selection if present
        setSelectedSlots(prev => prev.filter(s => s.id !== slotId))
        logger.info('Deleted avatar slot')
      }
    } catch (error) {
      logger.error('Failed to delete avatar slot:', error)
    }
  }

  const handleDeleteMultipleSlots = async () => {
    try {
      const deletePromises = selectedSlots.map(slot =>
        fetch(`${apiUrl}/api/avatar-slots/configured/${slot.id}`, { method: 'DELETE' })
      )
      await Promise.all(deletePromises)
      await loadConfiguredSlots()
      setSelectedSlots([])
      setSelectedSlot(null)
      logger.info(`Deleted ${selectedSlots.length} avatar slots`)
    } catch (error) {
      logger.error('Failed to delete multiple slots:', error)
    }
  }

  const handlePasteSlot = async () => {
    if (!copiedSlot) return
    
    try {
      if (copiedSlot.multiple) {
        // Paste multiple slots
        const maxIndex = configuredSlots.reduce((max, slot) => Math.max(max, slot.slot_index), -1)
        const newSlotIndices = []
        
        for (let i = 0; i < copiedSlot.slots.length; i++) {
          const slot = copiedSlot.slots[i]
          const newIndex = maxIndex + 1 + i
          newSlotIndices.push(newIndex)
          const newX = Math.round(Math.min(100, slot.x_position + 5))
          const newY = Math.round(Math.min(100, slot.y_position + 5))
          
          const response = await fetch(`${apiUrl}/api/avatar-slots/configured`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              slot_index: newIndex,
              x_position: newX,
              y_position: newY,
              size: slot.size,
              avatar_group_id: slot.avatar_group_id || null
            })
          })
          
          const data = await response.json()
          if (!data.success) {
            logger.error('Failed to create slot:', data)
          }
        }
        
        // Reload slots and get the updated list
        const updatedSlots = await loadConfiguredSlots()
        
        // Select the newly created slots and clear the old selection
        const newSlots = updatedSlots.filter(s => newSlotIndices.includes(s.slot_index))
        if (newSlots.length > 0) {
          setSelectedSlots(newSlots)
          setSelectedSlot(newSlots[0])
          logger.info(`Pasted and selected ${newSlots.length} slots`)
        }
      } else {
        // Paste single slot
        const maxIndex = configuredSlots.reduce((max, slot) => Math.max(max, slot.slot_index), -1)
        const newIndex = maxIndex + 1
        
        // Offset the position slightly so it doesn't overlap exactly
        const newX = Math.round(Math.min(100, copiedSlot.x_position + 5))
        const newY = Math.round(Math.min(100, copiedSlot.y_position + 5))
        
        const response = await fetch(`${apiUrl}/api/avatar-slots/configured`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            slot_index: newIndex,
            x_position: newX,
            y_position: newY,
            size: copiedSlot.size,
            avatar_group_id: copiedSlot.avatar_group_id || null
          })
        })
        
        const data = await response.json()
        if (data.success) {
          // Reload slots and get the updated list
          const updatedSlots = await loadConfiguredSlots()
          
          // Find and select the newly created slot, clear multi-selection
          const newSlot = updatedSlots.find(s => s.slot_index === newIndex)
          if (newSlot) {
            setSelectedSlot(newSlot)
            setSelectedSlots([]) // Clear multi-selection
            logger.info(`Pasted and selected slot #${newIndex + 1}`)
          }
        }
      }
    } catch (error) {
      logger.error('Error pasting slot:', error)
    }
  }

  const handleUpdateSlot = async (slotId, updates) => {
    try {
      const response = await fetch(`${apiUrl}/api/avatar-slots/configured/${slotId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      })
      
      const data = await response.json()
      if (data.success) {
        const updatedSlots = await loadConfiguredSlots()
        // Update selectedSlot if it's the one that was modified
        if (selectedSlot && selectedSlot.id === slotId) {
          const updatedSlot = updatedSlots.find(s => s.id === slotId)
          if (updatedSlot) {
            setSelectedSlot(updatedSlot)
          }
        }
        logger.info('Updated avatar slot')
      }
    } catch (error) {
      logger.error('Failed to update avatar slot:', error)
    }
  }

  const handleMoveSlotUp = async (slot) => {
    const sortedSlots = [...configuredSlots].sort((a, b) => b.slot_index - a.slot_index)
    const currentIndex = sortedSlots.findIndex(s => s.id === slot.id)
    
    // Can't move up if already at the top
    if (currentIndex === 0) return
    
    // Swap slot_index with the slot above it
    const slotAbove = sortedSlots[currentIndex - 1]
    const updates = [
      { id: slot.id, slot_index: slotAbove.slot_index },
      { id: slotAbove.id, slot_index: slot.slot_index }
    ]
    
    // Optimistically update local state
    const updatedSlots = configuredSlots.map(s => {
      const update = updates.find(u => u.id === s.id)
      return update ? { ...s, slot_index: update.slot_index } : s
    })
    setConfiguredSlots(updatedSlots)
    
    // Save to backend
    try {
      await Promise.all(updates.map(update =>
        fetch(`${apiUrl}/api/avatar-slots/configured/${update.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ slot_index: update.slot_index })
        })
      ))
      logger.info('Moved slot up')
    } catch (error) {
      logger.error('Failed to move slot:', error)
      await loadConfiguredSlots()
    }
  }

  const handleMoveSlotDown = async (slot) => {
    const sortedSlots = [...configuredSlots].sort((a, b) => b.slot_index - a.slot_index)
    const currentIndex = sortedSlots.findIndex(s => s.id === slot.id)
    
    // Can't move down if already at the bottom
    if (currentIndex === sortedSlots.length - 1) return
    
    // Swap slot_index with the slot below it
    const slotBelow = sortedSlots[currentIndex + 1]
    const updates = [
      { id: slot.id, slot_index: slotBelow.slot_index },
      { id: slotBelow.id, slot_index: slot.slot_index }
    ]
    
    // Optimistically update local state
    const updatedSlots = configuredSlots.map(s => {
      const update = updates.find(u => u.id === s.id)
      return update ? { ...s, slot_index: update.slot_index } : s
    })
    setConfiguredSlots(updatedSlots)
    
    // Save to backend
    try {
      await Promise.all(updates.map(update =>
        fetch(`${apiUrl}/api/avatar-slots/configured/${update.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ slot_index: update.slot_index })
        })
      ))
      logger.info('Moved slot down')
    } catch (error) {
      logger.error('Failed to move slot:', error)
      await loadConfiguredSlots()
    }
  }

  const handleCanvasClick = (e) => {
    // This is now handled by mouse down/up for box selection
  }

  const handleCanvasMouseDown = (e) => {
    if (e.target !== e.currentTarget) return // Only on canvas, not on slots
    
    const rect = e.currentTarget.getBoundingClientRect()
    const x = Math.round(((e.clientX - rect.left) / rect.width) * 100)
    const y = Math.round(((e.clientY - rect.top) / rect.height) * 100)
    
    // Start box selection
    setIsBoxSelecting(true)
    setBoxSelectStart({ x, y })
    setBoxSelectEnd({ x, y })
    
    // Clear selection if not holding Ctrl/Shift
    if (!e.ctrlKey && !e.shiftKey) {
      setSelectedSlot(null)
      setSelectedSlots([])
      setPendingClearMultiSelect(false)
    }
  }

  const handleMouseDown = (e, slot) => {
    e.stopPropagation()
    
    // Multi-selection with Ctrl/Cmd or Shift
    if (e.ctrlKey || e.metaKey || e.shiftKey) {
      setPendingClearMultiSelect(false)
      if (selectedSlots.find(s => s.id === slot.id)) {
        // Deselect if already selected
        setSelectedSlots(prev => prev.filter(s => s.id !== slot.id))
        if (selectedSlot?.id === slot.id) {
          setSelectedSlot(null)
        }
      } else {
        // Add to selection
        // If transitioning from single selection to multi-selection, include the previously selected slot
        if (selectedSlot && selectedSlots.length === 0) {
          setSelectedSlots([selectedSlot, slot])
        } else {
          setSelectedSlots(prev => [...prev, slot])
        }
        setSelectedSlot(slot)
      }
    } else {
      // Clicking without modifier keys
      if (selectedSlots.length > 0 && selectedSlots.find(s => s.id === slot.id)) {
        // Clicking on an already-selected item in multi-selection
        // Don't clear selection yet - allow dragging, but mark for potential clear on mouse up
        setPendingClearMultiSelect(true)
        setIsDragging(true)
        setDraggedSlot(slot) // Primary slot for drag offset calculation
        setDragOffset({ x: Math.round(slot.x_position), y: Math.round(slot.y_position) })
      } else {
        // Single selection - clear multi-selection immediately
        setPendingClearMultiSelect(false)
        setSelectedSlot(slot)
        setSelectedSlots([])
        setIsDragging(true)
        setDraggedSlot(slot)
        setDragOffset({ x: Math.round(slot.x_position), y: Math.round(slot.y_position) })
      }
    }
  }

  const handleMouseMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = Math.max(0, Math.min(100, Math.round(((e.clientX - rect.left) / rect.width) * 100)))
    const y = Math.max(0, Math.min(100, Math.round(((e.clientY - rect.top) / rect.height) * 100)))
    
    if (isBoxSelecting) {
      // Update box selection area
      setBoxSelectEnd({ x, y })
      
      // Calculate which slots are in the box
      const minX = Math.min(boxSelectStart.x, x)
      const maxX = Math.max(boxSelectStart.x, x)
      const minY = Math.min(boxSelectStart.y, y)
      const maxY = Math.max(boxSelectStart.y, y)
      
      const slotsInBox = configuredSlots.filter(slot => {
        return slot.x_position >= minX && slot.x_position <= maxX &&
               slot.y_position >= minY && slot.y_position <= maxY
      })
      
      setSelectedSlots(slotsInBox)
      if (slotsInBox.length > 0) {
        setSelectedSlot(slotsInBox[0])
      } else {
        setSelectedSlot(null)
      }
    } else if (isDragging && draggedSlot) {
      // User is actually dragging - clear the pending flag
      if (pendingClearMultiSelect && (x !== draggedSlot.x_position || y !== draggedSlot.y_position)) {
        setPendingClearMultiSelect(false)
      }
      // Update drag offset for visual feedback
      setDragOffset({ x, y })
    }
  }

  const handleMouseUp = async () => {
    // Flush any pending size updates immediately when mouse is released
    if (sizeUpdateTimeoutRef.current) {
      clearTimeout(sizeUpdateTimeoutRef.current)
      sizeUpdateTimeoutRef.current = null
    }
    if (pendingSizeUpdateRef.current) {
      await handleUpdateSlot(pendingSizeUpdateRef.current.slotId, { 
        size: pendingSizeUpdateRef.current.size 
      })
      pendingSizeUpdateRef.current = null
    }
    
    if (isBoxSelecting) {
      // End box selection
      setIsBoxSelecting(false)
      setBoxSelectStart({ x: 0, y: 0 })
      setBoxSelectEnd({ x: 0, y: 0 })
    } else if (isDragging && draggedSlot) {
      // Calculate movement delta
      const deltaX = dragOffset.x - draggedSlot.x_position
      const deltaY = dragOffset.y - draggedSlot.y_position
      const didActuallyDrag = deltaX !== 0 || deltaY !== 0
      
      // If we were pending a clear and user didn't actually drag, clear multi-selection now
      if (pendingClearMultiSelect && !didActuallyDrag) {
        setIsDragging(false)
        setDraggedSlot(null)
        setDragOffset({ x: 0, y: 0 })
        setPendingClearMultiSelect(false)
        setSelectedSlots([])
        setSelectedSlot(draggedSlot)
      } else if (selectedSlots.length > 0 && selectedSlots.find(s => s.id === draggedSlot.id)) {
        // Move all selected slots
        // Calculate updates based on the current configuredSlots to get accurate positions
        const updates = selectedSlots.map(slot => {
          const currentSlot = configuredSlots.find(s => s.id === slot.id)
          return {
            id: slot.id,
            x_position: Math.round(Math.max(0, Math.min(100, currentSlot.x_position + deltaX))),
            y_position: Math.round(Math.max(0, Math.min(100, currentSlot.y_position + deltaY)))
          }
        })
        
        // Update ALL state in a single batched operation to prevent intermediate renders
        // This ensures positions are updated atomically with drag state clearing
        const updatedSlots = configuredSlots.map(slot => {
          const update = updates.find(u => u.id === slot.id)
          return update ? { ...slot, x_position: update.x_position, y_position: update.y_position } : slot
        })
        
        const updatedSelectedSlots = selectedSlots.map(slot => {
          const update = updates.find(u => u.id === slot.id)
          return update ? { ...slot, x_position: update.x_position, y_position: update.y_position } : slot
        })
        
        // Batch all state updates together - React 18 automatically batches these
        setConfiguredSlots(updatedSlots)
        setSelectedSlots(updatedSelectedSlots)
        setIsDragging(false)
        setDraggedSlot(null)
        setDragOffset({ x: 0, y: 0 })
        setPendingClearMultiSelect(false)
        
        // Save all updates to backend in parallel, without reloading after each one
        try {
          await Promise.all(updates.map(update =>
            fetch(`${apiUrl}/api/avatar-slots/configured/${update.id}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                x_position: update.x_position,
                y_position: update.y_position
              })
            })
          ))
          logger.info(`Moved ${selectedSlots.length} slots`)
        } catch (error) {
          logger.error('Failed to update multiple slots:', error)
          // Reload on error to sync with backend
          await loadConfiguredSlots()
        }
      } else {
        // Move single slot
        const newX = dragOffset.x
        const newY = dragOffset.y
        
        // Clear drag state first
        setIsDragging(false)
        setDraggedSlot(null)
        setDragOffset({ x: 0, y: 0 })
        setPendingClearMultiSelect(false)
        
        // Update positions
        setConfiguredSlots(prev => prev.map(slot => 
          slot.id === draggedSlot.id 
            ? { ...slot, x_position: newX, y_position: newY }
            : slot
        ))
        
        // Update selected slot to reflect new position
        if (selectedSlot?.id === draggedSlot.id) {
          setSelectedSlot({ ...selectedSlot, x_position: newX, y_position: newY })
        }
        
        // Save to backend
        await handleUpdateSlot(draggedSlot.id, {
          x_position: newX,
          y_position: newY
        })
      }
    } else {
      // No dragging occurred, just clean up
      setIsDragging(false)
      setDraggedSlot(null)
      setDragOffset({ x: 0, y: 0 })
      setPendingClearMultiSelect(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <LayoutGrid className="w-5 h-5" />
          Avatar Layout Editor
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Canvas for visual editing */}
        <div className="border rounded-lg bg-muted/20 relative overflow-hidden"
          style={{ width: '100%', paddingBottom: '75%' }} // 4:3 aspect ratio
        >
          <div
            ref={canvasRef}
            className="absolute inset-0 cursor-crosshair select-none"
            onMouseDown={handleCanvasMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
          >
            {/* Grid background */}
            <div className="absolute inset-0 opacity-10 pointer-events-none"
              style={{
                backgroundImage: 'linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)',
                backgroundSize: '10% 10%'
              }}
            />
            
            {/* Box selection visual */}
            {isBoxSelecting && (
              <div
                className="absolute border-2 border-primary bg-primary/10 pointer-events-none"
                style={{
                  left: `${Math.min(boxSelectStart.x, boxSelectEnd.x)}%`,
                  top: `${Math.min(boxSelectStart.y, boxSelectEnd.y)}%`,
                  width: `${Math.abs(boxSelectEnd.x - boxSelectStart.x)}%`,
                  height: `${Math.abs(boxSelectEnd.y - boxSelectStart.y)}%`
                }}
              />
            )}
            
            {/* Render avatar slots */}
            {configuredSlots.map(slot => {
              const avatar = groupedAvatars.find(a => a.id === slot.avatar_group_id)
              const isSelected = selectedSlot?.id === slot.id || selectedSlots.find(s => s.id === slot.id)
              const isBeingDragged = isDragging && draggedSlot?.id === slot.id
              const isInMultiDrag = isDragging && selectedSlots.find(s => s.id === slot.id) && selectedSlots.find(s => s.id === draggedSlot?.id)
              
              // Calculate display position
              let displayX = slot.x_position
              let displayY = slot.y_position
              
              if (isBeingDragged) {
                displayX = dragOffset.x
                displayY = dragOffset.y
              } else if (isInMultiDrag && draggedSlot) {
                // Apply same delta to all selected slots
                const deltaX = dragOffset.x - draggedSlot.x_position
                const deltaY = dragOffset.y - draggedSlot.y_position
                displayX = Math.max(0, Math.min(100, slot.x_position + deltaX))
                displayY = Math.max(0, Math.min(100, slot.y_position + deltaY))
              }
              
              return (
                <div
                  key={slot.id}
                  className={`absolute cursor-move ${isSelected ? 'ring-2 ring-primary' : ''}`}
                  style={{
                    left: `${displayX}%`,
                    top: `${displayY}%`,
                    width: `${(slot.size / dimensions.width) * 100}%`,
                    height: `${(slot.size / dimensions.height) * 100}%`,
                    transform: 'translate(-50%, -50%)',
                    zIndex: slot.slot_index, // Use slot_index for stacking order
                  }}
                  onMouseDown={(e) => handleMouseDown(e, slot)}
                >
                  {avatar ? (
                    <img
                      src={`${apiUrl}${avatar.defaultImage}`}
                      alt={avatar.name}
                      className="w-full h-full object-contain rounded-full"
                      style={{ filter: avatar.disabled ? 'grayscale(100%)' : 'none' }}
                      draggable={false}
                      onDragStart={(e) => e.preventDefault()}
                    />
                  ) : (
                    <div className="w-full h-full rounded-full border-2 border-dashed border-muted-foreground/50 flex items-center justify-center text-xs text-muted-foreground">
                      Empty
                    </div>
                  )}
                  {isSelected && (
                    <div className="absolute -top-2 -right-2 w-6 h-6 bg-primary rounded-full flex items-center justify-center text-xs text-primary-foreground">
                      {slot.slot_index + 1}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Toolbar */}
        <div className="flex gap-2">
          <Button onClick={handleAddSlot} size="sm">
            <Plus className="w-4 h-4 mr-1" />
            Add Slot
          </Button>
          {selectedSlot && (
            <Button 
              onClick={() => handleDeleteSlot(selectedSlot.id)} 
              size="sm" 
              variant="destructive"
            >
              <Trash2 className="w-4 h-4 mr-1" />
              Delete Selected
            </Button>
          )}
        </div>

        {/* Selected slot editor */}
        {selectedSlot && (
          <div className="border rounded-lg p-4 space-y-4 bg-card">
            <h3 className="font-medium">
              Edit Slot #{selectedSlot.slot_index + 1}
            </h3>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>X Position (%)</Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  value={selectedSlot.x_position}
                  onChange={(e) => {
                    const value = parseInt(e.target.value)
                    setConfiguredSlots(prev => prev.map(slot =>
                      slot.id === selectedSlot.id
                        ? { ...slot, x_position: value }
                        : slot
                    ))
                    setSelectedSlot({ ...selectedSlot, x_position: value })
                  }}
                  onBlur={() => handleUpdateSlot(selectedSlot.id, { x_position: selectedSlot.x_position })}
                />
              </div>
              
              <div className="space-y-2">
                <Label>Y Position (%)</Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  value={selectedSlot.y_position}
                  onChange={(e) => {
                    const value = parseInt(e.target.value)
                    setConfiguredSlots(prev => prev.map(slot =>
                      slot.id === selectedSlot.id
                        ? { ...slot, y_position: value }
                        : slot
                    ))
                    setSelectedSlot({ ...selectedSlot, y_position: value })
                  }}
                  onBlur={() => handleUpdateSlot(selectedSlot.id, { y_position: selectedSlot.y_position })}
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Size (pixels)</Label>
              <Input
                type="number"
                min="20"
                max="200"
                value={selectedSlot.size}
                onChange={(e) => {
                  const value = parseInt(e.target.value) || 60
                  setConfiguredSlots(prev => prev.map(slot =>
                    slot.id === selectedSlot.id
                      ? { ...slot, size: value }
                      : slot
                  ))
                  setSelectedSlot({ ...selectedSlot, size: value })
                }}
                onBlur={() => handleUpdateSlot(selectedSlot.id, { size: selectedSlot.size })}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Assigned Avatar</Label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={selectedSlot.avatar_group_id || ''}
                onChange={(e) => {
                  const value = e.target.value || null
                  handleUpdateSlot(selectedSlot.id, { avatar_group_id: value })
                }}
              >
                <option value="">None (Empty Slot)</option>
                {groupedAvatars.filter(a => !a.disabled).map(avatar => (
                  <option key={avatar.id} value={avatar.id}>
                    {avatar.name}
                  </option>
                ))}
              </select>
            </div>
            
            <div className="space-y-2">
              <Label>Assigned Voice</Label>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                value={selectedSlot.voice_id || ''}
                onChange={(e) => {
                  const value = e.target.value ? parseInt(e.target.value) : null
                  handleUpdateSlot(selectedSlot.id, { voice_id: value })
                }}
              >
                <option value="">Random (Any Voice)</option>
                {voices.filter(v => v.enabled).map(voice => (
                  <option key={voice.id} value={voice.id}>
                    {voice.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        {configuredSlots.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            No avatar slots configured. Click "Add Slot" to create your first avatar position.
          </div>
        )}

        {/* Avatar slots list view */}
        {configuredSlots.length > 0 && (
          <div className="space-y-2">
            <h3 className="font-medium text-sm">Configured Avatar Slots ({configuredSlots.length})</h3>
            <p className="text-xs text-muted-foreground">Top items appear above bottom items</p>
            <div className="border rounded-lg divide-y max-h-64 overflow-y-auto">
              {configuredSlots
                .sort((a, b) => b.slot_index - a.slot_index)
                .map((slot, index) => {
                  const avatar = groupedAvatars.find(a => a.id === slot.avatar_group_id)
                  const isSelected = selectedSlot?.id === slot.id
                  const sortedSlots = [...configuredSlots].sort((a, b) => b.slot_index - a.slot_index)
                  const isFirst = index === 0
                  const isLast = index === sortedSlots.length - 1
                  
                  return (
                    <div
                      key={slot.id}
                      className={`flex items-center gap-3 p-3 hover:bg-muted/50 transition-colors ${
                        isSelected ? 'bg-muted' : ''
                      }`}
                    >
                      {/* Move up/down buttons */}
                      <div className="flex flex-col gap-1 flex-shrink-0">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-5 w-5 p-0"
                          disabled={isFirst}
                          onClick={(e) => {
                            e.stopPropagation()
                            handleMoveSlotUp(slot)
                          }}
                        >
                          <ChevronUp className="w-3 h-3" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-5 w-5 p-0"
                          disabled={isLast}
                          onClick={(e) => {
                            e.stopPropagation()
                            handleMoveSlotDown(slot)
                          }}
                        >
                          <ChevronDown className="w-3 h-3" />
                        </Button>
                      </div>
                      
                      {/* Avatar preview */}
                      <div 
                        className="w-12 h-12 rounded-full overflow-hidden flex-shrink-0 bg-muted flex items-center justify-center cursor-pointer"
                        onClick={() => setSelectedSlot(slot)}
                      >
                        {avatar ? (
                          <img
                            src={`${apiUrl}${avatar.defaultImage}`}
                            alt={avatar.name}
                            className="w-full h-full object-contain"
                            style={{ filter: avatar.disabled ? 'grayscale(100%)' : 'none' }}
                          />
                        ) : (
                          <div className="text-xs text-muted-foreground">Empty</div>
                        )}
                      </div>
                      
                      {/* Slot info */}
                      <div 
                        className="flex-1 min-w-0 cursor-pointer"
                        onClick={() => setSelectedSlot(slot)}
                      >
                        <div className="font-medium text-sm">
                          Slot #{slot.slot_index + 1}
                          {avatar && ` - ${avatar.name}`}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Position: ({slot.x_position}%, {slot.y_position}%) • Size: {slot.size}px
                        </div>
                      </div>
                      
                      {/* Delete button */}
                      <Button
                        size="sm"
                        variant="ghost"
                        className="flex-shrink-0 h-8 w-8 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteSlot(slot.id)
                        }}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  )
                })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default AvatarLayoutEditor
