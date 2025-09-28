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

    try {
      console.log('🔗 Global WebSocket connecting to', this.wsUrl, 'with', this.listeners.size, 'listeners')
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
        console.log('🔴 Global WebSocket disconnected:', event.code)
        this.connected = false
        this.ws = null
        
        // Only reconnect if we have listeners and it wasn't a clean close
        if (event.code !== 1000 && this.listeners.size > 0 && !this.reconnectTimer) {
          console.log('🔄 Global WebSocket reconnecting in 3 seconds...')
          this.reconnectTimer = setTimeout(() => {
            this.connect()
          }, 3000)
        }
      }

      this.ws.onerror = (err) => {
        console.error('❌ Global WebSocket error:', err)
        this.connected = false
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
    console.log('🔌 Global WebSocket disconnecting...')
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    
    if (this.ws) {
      this.ws.close(1000, 'No listeners')
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
