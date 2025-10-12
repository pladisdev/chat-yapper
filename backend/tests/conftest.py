"""Pytest configuration and fixtures for Chat Yapper tests"""
import os
import sys
import tempfile
from pathlib import Path
import pytest
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool
from fastapi.testclient import TestClient

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.models import Setting, Voice, AvatarImage


@pytest.fixture(name="session")
def session_fixture():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def test_db_path(tmp_path):
    """Create a temporary database file path"""
    db_path = tmp_path / "test_chat_yapper.db"
    return str(db_path)


@pytest.fixture
def test_audio_dir(tmp_path):
    """Create a temporary audio directory"""
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    return audio_dir


@pytest.fixture
def test_settings():
    """Provide default test settings"""
    return {
        "twitchChannel": "test_channel",
        "ttsProvider": "edge",
        "elevenLabsApiKey": "",
        "openaiApiKey": "",
        "azureSpeechKey": "",
        "azureSpeechRegion": "",
        "awsAccessKeyId": "",
        "awsSecretAccessKey": "",
        "awsRegion": "us-east-1",
        "avatarRows": 2,
        "avatarRowConfig": [6, 6],
        "minMessageLength": 1,
        "maxMessageLength": 500,
        "messageFilters": [],
        "userFilters": [],
        "commandPrefixFilter": "!",
        "enableCommandFilter": True,
    }


@pytest.fixture
def test_voice():
    """Create a test voice object"""
    return Voice(
        id=1,
        name="Test Voice",
        voice_id="en-US-GuyNeural",
        provider="edge",
        enabled=True,
        avatar_mode="single",
        avatar_image="test_avatar.png"
    )


@pytest.fixture
def test_avatar_image():
    """Create a test avatar image object"""
    return AvatarImage(
        id=1,
        name="Test Avatar",
        filename="test_avatar.png",
        file_path="/path/to/test_avatar.png",
        avatar_type="default",
        file_size=1024
    )


@pytest.fixture
def client():
    """Create a FastAPI test client"""
    # Import here to avoid circular imports
    from app import app
    
    # Create test client without database override
    # Tests will use the actual app database configuration
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables before each test"""
    # Store original environment
    original_env = os.environ.copy()
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
