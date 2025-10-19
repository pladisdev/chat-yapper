# Backend Tests

This directory contains automated tests for the Chat Yapper backend.

## Quick Start

```bash
# Install dependencies (from project root)
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

## Test Files

### Core Tests
- `test_models.py` - Database model tests (Setting, Voice, AvatarImage, YouTubeAuth)
- `test_tts.py` - TTS provider and synthesis tests
- `test_api.py` - FastAPI endpoint tests
- `test_message_filter.py` - Message filtering and spam detection tests
- `conftest.py` - Pytest fixtures and configuration

### Feature Tests (New)
- `test_audio_filters.py` - Audio post-processing filters (reverb, echo, pitch, speed, random)
- `test_config_backup.py` - Configuration export/import functionality
- `test_youtube.py` - YouTube Live Chat integration and OAuth
- `test_voice_management.py` - Voice CRUD operations and avatar modes
- `test_avatar_management.py` - Avatar upload, grouping, and positioning

## Running Specific Tests

```bash
# Run only model tests
pytest test_models.py

# Run only unit tests
pytest -m unit

# Run only API tests
pytest -m api

# Run only audio filter tests
pytest test_audio_filters.py

# Run only export/import tests
pytest test_config_backup.py

# Run only YouTube tests
pytest test_youtube.py

# Run only voice management tests
pytest test_voice_management.py

# Run only avatar tests
pytest test_avatar_management.py

# Skip slow tests
pytest -m "not slow"

# Run specific test class
pytest test_audio_filters.py::TestAudioFilterProcessor

# Run specific test function
pytest test_voice_management.py::TestVoiceAPIEndpoints::test_add_voice_success
```

## Test Markers

### General Markers
- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (slower, system-wide)
- `@pytest.mark.slow` - Slow-running tests (optional, skip with `-m "not slow"`)

### Feature Markers
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.tts` - TTS provider tests
- `@pytest.mark.models` - Database model tests
- `@pytest.mark.filtering` - Message filtering tests
- `@pytest.mark.audio` - Audio filter tests (NEW)
- `@pytest.mark.export_import` - Config export/import tests (NEW)
- `@pytest.mark.youtube` - YouTube integration tests (NEW)
- `@pytest.mark.voices` - Voice management tests (NEW)
- `@pytest.mark.avatars` - Avatar management tests (NEW)

## Test Coverage by Feature

### Audio Filters (`test_audio_filters.py`)
- ✅ FFmpeg detection and availability
- ✅ Reverb filter (room size, wetness)
- ✅ Echo filter (delay, decay)
- ✅ Pitch shift (up/down)
- ✅ Speed change (faster/slower)
- ✅ Random filter combinations
- ✅ Audio duration calculation
- ✅ Filter chain building
- ✅ Edge case handling (extreme values)

### Export/Import (`test_config_backup.py`)
- ✅ Configuration export to ZIP
- ✅ Export structure validation
- ✅ Settings, voices, and avatars export
- ✅ Import from ZIP file
- ✅ Replace vs merge modes
- ✅ Database backup creation
- ✅ Import statistics and error handling
- ✅ Round-trip export/import cycle

### YouTube Integration (`test_youtube.py`)
- ✅ YouTubeAuth model CRUD
- ✅ OAuth flow (start, callback, disconnect)
- ✅ Connection status endpoint
- ✅ Token management and refresh
- ✅ Live stream detection
- ✅ Chat message processing
- ✅ Event mapping (Super Chat→bits, memberships→sub)
- ✅ User badge mapping (owner, mod, member→vip)

### Voice Management (`test_voice_management.py`)
- ✅ Voice model CRUD operations
- ✅ Single vs dual avatar modes
- ✅ Voice provider support (Edge, Monster, Google, Polly)
- ✅ Duplicate voice detection
- ✅ Voice enable/disable
- ✅ API endpoints (add, update, delete, list)
- ✅ Available voices fetching

### Avatar Management (`test_avatar_management.py`)
- ✅ Avatar model CRUD operations
- ✅ Avatar upload handling
- ✅ Avatar grouping (avatar_group_id)
- ✅ Spawn position management
- ✅ Avatar types (default, speaking, custom)
- ✅ Enable/disable avatars
- ✅ Metadata (upload date, file size)
- ✅ API endpoints (upload, list, update, delete)

## Running Tests by Category

```bash
# Run all audio filter tests
pytest -m audio

# Run all export/import tests
pytest -m export_import

# Run all YouTube tests
pytest -m youtube

# Run all voice management tests
pytest -m voices

# Run all avatar management tests
pytest -m avatars

# Run all new feature tests
pytest -m "audio or export_import or youtube or voices or avatars"

# Run only unit tests for new features
pytest -m "unit and (audio or export_import or youtube or voices or avatars)"
```

## Test Requirements

Some tests require specific dependencies or system tools:

- **Audio filter tests**: Require ffmpeg installed and available in PATH
  - Skip audio tests if ffmpeg not available: `pytest -m "not audio"`
  
- **YouTube tests**: Mock Google API calls (no real API key needed)
  
- **Export/import tests**: Create temporary files and directories

## Continuous Integration

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`

GitHub Actions workflow runs:
- Backend tests (Python 3.9, 3.10, 3.11)
- Frontend tests (Node.js 18, 20)
- Linting and formatting checks
- Coverage reporting to Codecov

See `../.github/workflows/tests.yml` for workflow configuration.

## Test Fixtures

Common fixtures available in `conftest.py`:

- `session` - Database session for tests
- `client` - FastAPI test client
- `sample_audio_file` - Temporary audio file (audio tests)
- `message_history` - Message filter history (filter tests)

## Best Practices

1. **Use appropriate markers** - Tag tests with relevant markers
2. **Mock external APIs** - Don't make real API calls in tests
3. **Clean up resources** - Use fixtures and teardown for temp files
4. **Test edge cases** - Include tests for invalid input and errors
5. **Keep tests fast** - Mark slow tests with `@pytest.mark.slow`
6. **Isolate tests** - Tests should not depend on each other

## Troubleshooting

### Tests fail with "ffmpeg not found"
- Install ffmpeg: `choco install ffmpeg` (Windows) or `brew install ffmpeg` (Mac)
- Or skip audio tests: `pytest -m "not audio"`

### Import errors
- Ensure dependencies installed: `pip install -r requirements.txt`
- Check Python path includes backend directory

### Database errors
- Tests use in-memory SQLite database
- Each test gets fresh database via fixtures

See `../TESTING.md` for complete documentation.
