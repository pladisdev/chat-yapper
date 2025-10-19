import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { History, RefreshCw, Play } from 'lucide-react'
import logger from '../utils/logger'

export default function MessageHistory({ apiUrl }) {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [replayingId, setReplayingId] = useState(null)

  const fetchHistory = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${apiUrl}/api/test/message-history`)
      const data = await response.json()
      
      if (data.success) {
        setMessages(data.messages)
        logger.info(`Loaded ${data.messages.length} messages from history`)
      } else {
        setError(data.error || 'Failed to load message history')
      }
    } catch (err) {
      logger.error('Failed to fetch message history:', err)
      setError('Failed to connect to server')
    } finally {
      setLoading(false)
    }
  }

  const replayMessage = async (message) => {
    const messageId = `${message.timestamp}-${message.username}`
    setReplayingId(messageId)
    
    try {
      logger.info(`Replaying message from ${message.username}: ${message.original_text}`)
      const response = await fetch(`${apiUrl}/api/test/replay-message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: message.username,
          text: message.original_text,
          eventType: message.event_type
        })
      })
      
      const data = await response.json()
      
      if (data.success) {
        logger.info('Message replayed successfully')
      } else {
        logger.error('Failed to replay message:', data.error)
      }
    } catch (err) {
      logger.error('Failed to replay message:', err)
    } finally {
      setTimeout(() => setReplayingId(null), 1000)
    }
  }

  useEffect(() => {
    fetchHistory()
    
    // Auto-refresh every 5 seconds
    const interval = setInterval(fetchHistory, 5000)
    return () => clearInterval(interval)
  }, [apiUrl])

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp * 1000)
    return date.toLocaleTimeString()
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <History className="w-5 h-5" />
              Message History & Replay
            </CardTitle>
            <CardDescription>
              Last 100 processed messages - click to replay and test filtering changes
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchHistory}
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {error && (
          <div className="p-4 mb-4 rounded-lg bg-destructive/10 text-destructive text-sm">
            {error}
          </div>
        )}
        
        {messages.length === 0 && !loading && (
          <div className="text-center py-8 text-muted-foreground">
            <History className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No messages in history yet</p>
            <p className="text-sm mt-1">Send test messages to see them here</p>
          </div>
        )}
        
        {messages.length > 0 && (
          <div className="h-[500px] overflow-y-auto pr-4">
            <div className="space-y-3">
              {messages.map((msg, index) => {
                const messageId = `${msg.timestamp}-${msg.username}`
                const isReplaying = replayingId === messageId
                
                return (
                  <div
                    key={index}
                    className="group relative p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors cursor-pointer"
                    onClick={() => !isReplaying && replayMessage(msg)}
                  >
                    {/* Header */}
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{msg.username}</span>
                        <span className="text-xs text-muted-foreground">
                          {formatTimestamp(msg.timestamp)}
                        </span>
                        {msg.event_type !== 'chat' && (
                          <span className="text-xs px-2 py-0.5 rounded bg-primary/10 text-primary">
                            {msg.event_type}
                          </span>
                        )}
                      </div>
                      
                      <Button
                        variant="ghost"
                        size="sm"
                        className="opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={(e) => {
                          e.stopPropagation()
                          replayMessage(msg)
                        }}
                        disabled={isReplaying}
                      >
                        {isReplaying ? (
                          <>
                            <RefreshCw className="w-4 h-4 mr-1 animate-spin" />
                            Replaying...
                          </>
                        ) : (
                          <>
                            <Play className="w-4 h-4 mr-1" />
                            Replay
                          </>
                        )}
                      </Button>
                    </div>
                    
                    {/* Messages */}
                    <div className="space-y-2">
                      <div>
                        <span className="text-xs font-medium text-muted-foreground">Original:</span>
                        <p className="text-sm mt-1">{msg.original_text}</p>
                      </div>
                      
                      {msg.was_filtered && (
                        <div>
                          <span className="text-xs font-medium text-muted-foreground">After Filter:</span>
                          <p className="text-sm mt-1 text-blue-600 dark:text-blue-400">
                            {msg.filtered_text}
                          </p>
                        </div>
                      )}
                      
                      {!msg.was_filtered && (
                        <p className="text-xs text-green-600 dark:text-green-400">
                          ✓ No filtering applied
                        </p>
                      )}
                    </div>
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
