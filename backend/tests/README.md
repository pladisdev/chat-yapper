# Backend Tests

This directory contains automated tests for the Chat Yapper backend.

## Quick Start

```bash
# Install dependencies
pip install -r ../requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

## Test Files

- `test_models.py` - Database model tests (Setting, Voice, AvatarImage)
- `test_tts.py` - TTS provider and synthesis tests
- `test_api.py` - FastAPI endpoint tests
- `conftest.py` - Pytest fixtures and configuration

## Running Specific Tests

```bash
# Run only model tests
pytest test_models.py

# Run only unit tests
pytest -m unit

# Run only API tests
pytest -m api

# Skip slow tests
pytest -m "not slow"
```

## Test Markers

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.api` - API tests
- `@pytest.mark.tts` - TTS tests
- `@pytest.mark.models` - Model tests
- `@pytest.mark.slow` - Slow-running tests

See `../TESTING.md` for complete documentation.
