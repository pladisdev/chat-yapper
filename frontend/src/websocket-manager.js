// Global WebSocket singleton - completely outside React
class WebSocketManager {
  constructor() {
    this.ws = null
    this.listeners = new Set()
    this.reconnectTimer = null
    this.wsUrl = null
    this.connected = false
  }

  init() {
    if (!this.wsUrl) {
      this.wsUrl = location.hostname === 'localhost' && (location.port === '5173' || location.port === '5174')
        ? 'ws://localhost:8000/ws'
        : `ws://${location.host}/ws`
    }
  }

  connect() {
    // Prevent multiple connections
    if (this.ws && (this.ws.readyState === WebSocket.CONNECTING || this.ws.readyState === WebSocket.OPEN)) {
      console.log('⚠️ WebSocket already connecting/connected, skipping')
      return
    }

    if (this.listeners.size === 0) {
      console.log('⚠️ No listeners, skipping connection')
      return
    }

    // Clear any existing reconnect timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    // Clean up any closed WebSocket instance
    if (this.ws && this.ws.readyState === WebSocket.CLOSED) {
      this.ws = null
    }

    try {
      console.log('🔗 Connecting WebSocket to', this.wsUrl, '(', this.listeners.size, 'listeners)')
      this.ws = new WebSocket(this.wsUrl)

      this.ws.onopen = () => {
        console.log('🟢 Global WebSocket connected, listeners:', this.listeners.size)
        this.connected = true
        this.ws.send('hello')
        
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer)
          this.reconnectTimer = null
        }
      }

      this.ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data)
          console.log('📨 Global WebSocket broadcasting to', this.listeners.size, 'listeners:', data.type)
          
          // Create array to avoid Set modification during iteration
          const listenerArray = Array.from(this.listeners)
          listenerArray.forEach(listener => {
            try {
              listener(data)
            } catch (error) {
              console.error('❌ Listener error:', error)
            }
          })
        } catch (error) {
          console.error('❌ Failed to parse WebSocket message:', error)
        }
      }

      this.ws.onclose = (event) => {
        this.connected = false
        const wsInstance = this.ws
        this.ws = null
        
        // Determine if this is an expected close
        const isCleanClose = event.code === 1000
        const isAbnormalClose = event.code === 1006
        const hasListeners = this.listeners.size > 0
        
        if (isCleanClose) {
          console.log('🔴 WebSocket closed cleanly (code 1000)')
        } else if (isAbnormalClose) {
          // Only log if we have listeners (otherwise it's expected cleanup)
          if (hasListeners) {
            console.log('⚠️ WebSocket closed abnormally (code 1006) - server may have restarted')
          } else {
            console.log('🔴 WebSocket closed (cleanup)')
          }
        } else {
          console.log('🔴 WebSocket disconnected with code:', event.code)
        }
        
        // Only reconnect if we have listeners and it wasn't a clean close
        if (!isCleanClose && hasListeners && !this.reconnectTimer) {
          console.log('🔄 Reconnecting in 3 seconds...')
          this.reconnectTimer = setTimeout(() => {
            if (this.listeners.size > 0) { // Double-check we still have listeners
              this.connect()
            }
          }, 3000)
        }
      }

      this.ws.onerror = (err) => {
        this.connected = false
        
        // Only log errors if we're not in the process of disconnecting
        if (this.ws && this.ws.readyState !== WebSocket.CLOSING && this.ws.readyState !== WebSocket.CLOSED) {
          console.error('❌ WebSocket error during connection')
        } else if (this.listeners.size > 0) {
          // Only log if we still have active listeners (not during cleanup)
          console.log('⚠️ WebSocket error during disconnect (expected)')
        }
        // Suppress error logging during cleanup when no listeners remain
      }
    } catch (error) {
      console.error('❌ Global WebSocket connection failed:', error)
      this.connected = false
    }
  }

  addListener(listener) {
    console.log('➕ Adding global listener. Total:', this.listeners.size + 1)
    this.listeners.add(listener)
    
    // Start connection if this is the first listener
    if (this.listeners.size === 1) {
      this.init()
      this.connect()
    }
    
    return () => {
      console.log('➖ Removing global listener. Remaining:', this.listeners.size - 1)
      this.listeners.delete(listener)
      
      // Close connection if no listeners remain
      if (this.listeners.size === 0) {
        this.disconnect()
      }
    }
  }

  disconnect() {
    console.log('🔌 Disconnecting WebSocket (no listeners)...')
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    
    if (this.ws) {
      const readyState = this.ws.readyState
      
      // Only close if not already closing/closed
      if (readyState === WebSocket.OPEN || readyState === WebSocket.CONNECTING) {
        try {
          this.ws.close(1000, 'No listeners')
        } catch (error) {
          // Suppress expected errors during cleanup
          console.log('⚠️ WebSocket close error (expected):', error.message)
        }
      }
      this.ws = null
    }
    
    this.connected = false
  }

  isConnected() {
    return this.connected
  }
}

// Create the single global instance
const globalWebSocketManager = new WebSocketManager()

export default globalWebSocketManager
