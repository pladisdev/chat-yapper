import React, { createContext, useContext, useCallback } from 'react'
import globalWebSocketManager from './websocket-manager'

const WebSocketContext = createContext()

export const useWebSocket = () => {
  const context = useContext(WebSocketContext)
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}

export const WebSocketProvider = ({ children }) => {
  const addListener = useCallback((listener) => {
    return globalWebSocketManager.addListener(listener)
  }, [])

  const value = {
    addListener
  }

  return (
    <WebSocketContext.Provider value={value}>
      {children}
    </WebSocketContext.Provider>
  )
}
