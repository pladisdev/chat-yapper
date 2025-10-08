# Frontend Tests

This directory contains automated tests for the Chat Yapper React frontend.

## Quick Start

```bash
# Install dependencies (from frontend directory)
cd ..
npm install

# Run tests in watch mode
npm test

# Run tests once
npm test -- --run

# Run with coverage
npm run test:coverage
```

## Test Files

- `setup.js` - Global test setup and mocks
- `App.test.jsx` - Main App component tests
- `WebSocketContext.test.jsx` - WebSocket context tests
- `utils.test.jsx` - Utility function tests

## Running Specific Tests

```bash
# Run specific test file
npm test -- App.test.jsx

# Run tests matching pattern
npm test -- --grep "WebSocket"

# Run with UI
npm run test:ui
```

## Writing Tests

```javascript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MyComponent from '../MyComponent'

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />)
    expect(screen.getByText('Hello')).toBeDefined()
  })
})
```

See `../../TESTING.md` for complete documentation.
