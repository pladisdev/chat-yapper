import React, { useState, useEffect } from 'react'
import { X, Volume2, VolumeX, MousePointer2 } from 'lucide-react'

const Toast = ({ message, type = 'info', onClose, autoClose = true, duration = 8000 }) => {
  useEffect(() => {
    if (autoClose) {
      const timer = setTimeout(onClose, duration)
      return () => clearTimeout(timer)
    }
  }, [autoClose, duration, onClose])

  const getIcon = () => {
    switch (type) {
      case 'error':
        return <VolumeX className="w-5 h-5" />
      case 'warning':
        return <Volume2 className="w-5 h-5" />
      case 'info':
      default:
        return <MousePointer2 className="w-5 h-5" />
    }
  }

  const getTypeClasses = () => {
    switch (type) {
      case 'error':
        return 'bg-red-600 border-red-500 text-white'
      case 'warning':
        return 'bg-yellow-600 border-yellow-500 text-white'
      case 'info':
      default:
        return 'bg-blue-600 border-blue-500 text-white'
    }
  }

  return (
    <div 
      className={`
        fixed bottom-6 left-6 z-[200] max-w-sm p-3 rounded-lg border-2 shadow-xl
        ${getTypeClasses()}
      `}
      style={{
        animation: 'slideInFromLeft 300ms ease-out'
      }}
    >
      <div className="flex items-start gap-2">
        {getIcon()}
        <div className="flex-1 text-xs font-medium leading-tight">
          {typeof message === 'string' ? <div>{message}</div> : message}
        </div>
        <button
          onClick={onClose}
          className="flex-shrink-0 p-1 rounded hover:bg-white/20 transition-colors"
          aria-label="Close notification"
        >
          <X className="w-3 h-3" />
        </button>
      </div>
    </div>
  )
}

export default Toast