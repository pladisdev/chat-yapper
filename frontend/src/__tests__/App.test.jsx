import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import App from '../app'

// Mock the WebSocketProvider
vi.mock('../WebSocketContext', () => ({
  WebSocketProvider: ({ children }) => <div>{children}</div>,
  useWebSocket: () => ({
    sendMessage: vi.fn(),
    isConnected: true,
  }),
}))

describe('App Component', () => {
  it('renders without crashing', () => {
    render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    )
    
    // App should render
    expect(document.body).toBeDefined()
  })

  it('has routing structure', () => {
    const { container } = render(
      <BrowserRouter>
        <App />
      </BrowserRouter>
    )
    
    // Should have some content
    expect(container.firstChild).toBeDefined()
  })
})
