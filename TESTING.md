# Chat Yapper Testing Guide

Comprehensive testing documentation for the Chat Yapper project, covering backend (Python/FastAPI) and frontend (React) testing.

## Table of Contents

- [Overview](#overview)
- [Backend Testing](#backend-testing)
- [Frontend Testing](#frontend-testing)
- [Running Tests Locally](#running-tests-locally)
- [Continuous Integration](#continuous-integration)
- [Writing New Tests](#writing-new-tests)
- [Test Coverage](#test-coverage)
- [Troubleshooting](#troubleshooting)

## Overview

Chat Yapper uses automated unit testing to ensure code quality and prevent regressions. The test suite includes:

- **Backend Tests**: Python tests using pytest for FastAPI endpoints, database models, and TTS functionality
- **Frontend Tests**: JavaScript/React tests using Vitest and React Testing Library
- **CI/CD**: Automated testing via GitHub Actions on every push and pull request

### Test Types

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test interactions between multiple components
- **API Tests**: Test FastAPI endpoints with TestClient
- **Component Tests**: Test React components with user interactions

## Backend Testing

### Technology Stack

- **pytest**: Testing framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Code coverage reporting
- **httpx**: FastAPI TestClient support
- **SQLModel**: In-memory database for testing

### Backend Test Structure

```
backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest configuration and fixtures
│   ├── test_models.py       # Database model tests
│   ├── test_tts.py          # TTS provider tests
│   └── test_api.py          # API endpoint tests
├── pytest.ini               # Pytest configuration
└── requirements.txt         # Includes testing dependencies
```

### Running Backend Tests

```bash
# Navigate to backend directory
cd backend

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_models.py

# Run specific test class
pytest tests/test_models.py::TestVoice

# Run specific test
pytest tests/test_models.py::TestVoice::test_create_voice_minimal

# Run tests by marker
pytest -m unit          # Only unit tests
pytest -m integration   # Only integration tests
pytest -m api           # Only API tests
pytest -m tts           # Only TTS tests

# Run with coverage report
pytest --cov=. --cov-report=html --cov-report=term-missing

# Run and skip slow tests
pytest -m "not slow"
```

### Backend Test Markers

Tests are organized with markers for easy filtering:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.tts` - TTS functionality tests
- `@pytest.mark.models` - Database model tests
- `@pytest.mark.slow` - Tests that take longer to run

### Backend Test Fixtures

Available fixtures in `conftest.py`:

- `session` - In-memory SQLite database session
- `test_db_path` - Temporary database file path
- `test_audio_dir` - Temporary audio directory
- `test_settings` - Default test settings dictionary
- `test_voice` - Pre-configured Voice object
- `test_avatar_image` - Pre-configured AvatarImage object
- `client` - FastAPI TestClient with database override

## Frontend Testing

### Technology Stack

- **Vitest**: Fast unit test framework (Vite-native)
- **React Testing Library**: React component testing utilities
- **jsdom**: Browser environment simulation
- **@testing-library/user-event**: User interaction simulation
- **@testing-library/jest-dom**: Custom matchers

### Frontend Test Structure

```
frontend/
├── src/
│   ├── __tests__/
│   │   ├── setup.js              # Test setup and global mocks
│   │   ├── App.test.jsx          # App component tests
│   │   ├── WebSocketContext.test.jsx  # WebSocket tests
│   │   └── utils.test.jsx        # Utility function tests
│   └── components/
├── vitest.config.js              # Vitest configuration
└── package.json                  # Includes testing scripts
```

### Running Frontend Tests

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (if not already installed)
npm install

# Run tests in watch mode (default)
npm test

# Run tests once (CI mode)
npm test -- --run

# Run with UI
npm run test:ui

# Run with coverage
npm run test:coverage

# Run specific test file
npm test -- WebSocketContext.test.jsx

# Update snapshots (if using snapshot testing)
npm test -- -u
```

### Frontend Test Scripts

Available in `package.json`:

- `npm test` - Run tests in watch mode
- `npm run test:ui` - Open Vitest UI in browser
- `npm run test:coverage` - Generate coverage report

### Writing Frontend Tests

Example test structure:

```javascript
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import MyComponent from '../MyComponent'

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />)
    expect(screen.getByText('Hello')).toBeDefined()
  })

  it('handles user interaction', async () => {
    const handleClick = vi.fn()
    render(<MyComponent onClick={handleClick} />)
    
    const button = screen.getByRole('button')
    await userEvent.click(button)
    
    expect(handleClick).toHaveBeenCalled()
  })
})
```

## Running Tests Locally

### Prerequisites

**Backend:**
- Python 3.9 or higher
- pip

**Frontend:**
- Node.js 16 or higher
- npm

### Quick Start

```bash
# Clone repository
git clone https://github.com/pladisdev/chat-yapper.git
cd chat-yapper

# Backend tests
cd backend
pip install -r requirements.txt
pytest

# Frontend tests
cd ../frontend
npm install
npm test -- --run
```

### Running All Tests

```bash
# From project root, run backend tests
cd backend && pytest && cd ..

# Run frontend tests
cd frontend && npm test -- --run && cd ..
```

## Continuous Integration

### GitHub Actions Workflow

The project uses GitHub Actions for automated testing on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Manual workflow dispatch

### Workflow Jobs

1. **Backend Tests**
   - Runs on Python 3.9, 3.10, and 3.11
   - Executes pytest with coverage
   - Uploads coverage to Codecov

2. **Frontend Tests**
   - Runs on Node.js 18.x and 20.x
   - Executes Vitest with coverage
   - Uploads coverage to Codecov

3. **Lint and Format**
   - Checks Python code formatting (black, isort, flake8)
   - Reports style violations

4. **Integration Tests**
   - Runs after unit tests pass
   - Tests backend and frontend together

5. **Test Summary**
   - Aggregates all test results
   - Fails if any critical tests fail

### Viewing CI Results

- Go to the "Actions" tab in GitHub repository
- Select a workflow run to see detailed results
- Check individual job logs for failures

## Writing New Tests

### Backend Test Guidelines

1. **Use appropriate markers**:
   ```python
   @pytest.mark.unit
   @pytest.mark.models
   def test_something(self, session):
       pass
   ```

2. **Use fixtures for setup**:
   ```python
   def test_with_voice(self, session, test_voice):
       session.add(test_voice)
       session.commit()
       # Test code here
   ```

3. **Test both success and failure cases**:
   ```python
   def test_valid_input(self):
       result = function(valid_data)
       assert result.is_valid
   
   def test_invalid_input(self):
       with pytest.raises(ValueError):
           function(invalid_data)
   ```

4. **Use descriptive test names**:
   ```python
   def test_voice_is_disabled_when_enabled_set_to_false(self):
       pass
   ```

### Frontend Test Guidelines

1. **Test user behavior, not implementation**:
   ```javascript
   // Good
   it('displays error when form is submitted empty', async () => {
     render(<Form />)
     await userEvent.click(screen.getByRole('button', { name: /submit/i }))
     expect(screen.getByText(/required/i)).toBeDefined()
   })
   
   // Avoid
   it('sets error state to true', () => {
     // Testing internal state
   })
   ```

2. **Use Testing Library queries properly**:
   ```javascript
   // Preferred (accessible)
   screen.getByRole('button', { name: /submit/i })
   screen.getByLabelText(/username/i)
   
   // Less preferred
   screen.getByTestId('submit-button')
   ```

3. **Mock external dependencies**:
   ```javascript
   vi.mock('../api', () => ({
     fetchData: vi.fn(() => Promise.resolve({ data: [] }))
   }))
   ```

## Test Coverage

### Viewing Coverage Reports

**Backend:**
```bash
cd backend
pytest --cov=. --cov-report=html
# Open htmlcov/index.html in browser
```

**Frontend:**
```bash
cd frontend
npm run test:coverage
# Open coverage/index.html in browser
```

### Coverage Goals

- **Overall**: Aim for 80%+ coverage
- **Critical paths**: 90%+ coverage (TTS, API endpoints)
- **New code**: Must include tests

### Excluding Files from Coverage

**Backend** (`pytest.ini`):
```ini
--cov-exclude-dirs=tests,public,.venv
```

**Frontend** (`vitest.config.js`):
```javascript
coverage: {
  exclude: ['node_modules/', 'src/__tests__/', '**/dist/**']
}
```

## Troubleshooting

### Common Issues

#### Backend Tests

**Issue**: `Import "pytest" could not be resolved`
```bash
# Solution: Install test dependencies
pip install -r requirements.txt
```

**Issue**: Database errors in tests
```bash
# Solution: Tests use in-memory SQLite, check session fixture
# Ensure you're using the session fixture provided
```

**Issue**: Async tests failing
```bash
# Solution: Mark async tests with @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result
```

#### Frontend Tests

**Issue**: `Cannot find module 'vitest'`
```bash
# Solution: Install dependencies
npm install
```

**Issue**: Tests timing out
```javascript
// Solution: Increase timeout or use waitFor
await waitFor(() => {
  expect(screen.getByText('Loaded')).toBeDefined()
}, { timeout: 5000 })
```

**Issue**: WebSocket mock issues
```javascript
// Solution: Mock in setup.js or individual test
global.WebSocket = vi.fn(() => ({
  addEventListener: vi.fn(),
  send: vi.fn(),
  close: vi.fn()
}))
```

### Getting Help

- Check test output for detailed error messages
- Review CI logs in GitHub Actions
- Ensure all dependencies are installed
- Check that you're in the correct directory
- Verify Python/Node.js versions

## Best Practices

1. **Write tests first** (TDD when possible)
2. **Keep tests isolated** - No dependencies between tests
3. **Use descriptive names** - Test names should describe behavior
4. **Test edge cases** - Not just happy paths
5. **Mock external services** - Don't rely on external APIs
6. **Keep tests fast** - Mark slow tests appropriately
7. **Maintain tests** - Update tests when code changes
8. **Review coverage** - Aim for high coverage of critical code

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Vitest Documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

---

For questions or issues with testing, please open an issue in the GitHub repository.
