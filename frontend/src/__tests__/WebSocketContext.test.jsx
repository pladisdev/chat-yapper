import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { WebSocketProvider } from '../WebSocketContext'

describe('WebSocketContext', () => {
  beforeEach(() => {
    // Mock WebSocket
    global.WebSocket = vi.fn(() => ({
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      send: vi.fn(),
      close: vi.fn(),
      readyState: 1,
    }))
  })

  it('provides WebSocket context to children', () => {
    const TestComponent = () => {
      return <div>Test Component</div>
    }

    render(
      <WebSocketProvider>
        <TestComponent />
      </WebSocketProvider>
    )

    expect(screen.getByText('Test Component')).toBeDefined()
  })
})
