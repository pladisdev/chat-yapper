import { useState, useCallback } from 'react'

export const useToast = () => {
  const [toasts, setToasts] = useState([])

  const showToast = useCallback((message, type = 'info', options = {}) => {
    const id = Date.now() + Math.random()
    const newToast = {
      id,
      message,
      type,
      ...options
    }

    setToasts(prev => {
      // Prevent duplicate messages of the same type
      const isDuplicate = prev.some(toast => 
        toast.message === message && toast.type === type
      )
      if (isDuplicate) {
        return prev
      }
      return [...prev, newToast]
    })
    return id
  }, [])

  const hideToast = useCallback((id) => {
    setToasts(prev => prev.filter(toast => toast.id !== id))
  }, [])

  const showAutoplayError = useCallback(() => {
    return showToast(
      '🔊 Audio blocked! Click anywhere to enable TTS.',
      'warning',
      { autoClose: false } // Don't auto-close this important message
    )
  }, [showToast])

  const hideAllToasts = useCallback(() => {
    setToasts([])
  }, [])

  return {
    toasts,
    showToast,
    hideToast,
    showAutoplayError,
    hideAllToasts
  }
}