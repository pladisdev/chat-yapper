from __future__ import annotations
from typing import Optional, Any
from sqlmodel import SQLModel, Field


class Setting(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str
    value_json: str # raw JSON string


class Voice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # Display name for the voice
    voice_id: str  # The actual voice ID used by the provider
    provider: str  # "monstertts" or "edge"
    enabled: bool = Field(default=True)  # Whether this voice is enabled for avatars
    avatar_image: Optional[str] = Field(default=None)  # Optional avatar image filename (legacy/single mode)
    avatar_default: Optional[str] = Field(default=None)  # Default/idle avatar image
    avatar_speaking: Optional[str] = Field(default=None)  # Speaking avatar image
    avatar_mode: str = Field(default="single")  # "single" or "dual" mode
    created_at: Optional[str] = Field(default=None)  # Timestamp when added


class AvatarImage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # Display name for the avatar
    filename: str  # Actual filename on disk
    file_path: str  # Full path to the file
    upload_date: Optional[str] = Field(default=None)  # When it was uploaded
    file_size: Optional[int] = Field(default=None)  # File size in bytes
    avatar_type: str = Field(default="default")  # "default" or "speaking"
    avatar_group_id: Optional[str] = Field(default=None)  # Group ID to link default and speaking images
    voice_id: Optional[int] = Field(default=None)  # ID of the Voice this avatar is assigned to (None = random)
    spawn_position: Optional[int] = Field(default=None)  # Specific slot number (1-6), None = random spawning
    disabled: bool = Field(default=False)  # Whether this avatar is disabled and should not be used


class TwitchAuth(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    twitch_user_id: str  # Twitch user ID
    username: str  # Twitch username
    display_name: str  # Twitch display name
    access_token: str  # OAuth access token
    refresh_token: str  # OAuth refresh token for renewals
    expires_at: Optional[str] = Field(default=None)  # When the access token expires
    created_at: Optional[str] = Field(default=None)  # When this auth was created
    updated_at: Optional[str] = Field(default=None)  # Last time tokens were refreshed


class YouTubeAuth(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    channel_id: str  # YouTube channel ID
    channel_name: str  # YouTube channel name
    access_token: str  # OAuth access token
    refresh_token: str  # OAuth refresh token for renewals
    expires_at: Optional[str] = Field(default=None)  # When the access token expires
    created_at: Optional[str] = Field(default=None)  # When this auth was created
    updated_at: Optional[str] = Field(default=None)  # Last time tokens were refreshed


class ProviderVoiceCache(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    provider: str  # Provider name (e.g., "polly", "monstertts", "google")
    voices_json: str  # JSON string of voice list
    last_updated: str  # ISO timestamp of when this was last fetched
    credentials_hash: Optional[str] = Field(default=None)  # Hash of credentials to detect changes