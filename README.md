# Chat Yapper

**Voice Avatar TTS System for Twitch Chat**

Chat Yapper is a powerful text-to-speech application that reads Twitch chat messages aloud using customizable voice avatars. Perfect for streamers who want to engage with their chat through voice while maintaining visual focus on their game or content.

## Features
- **Voice Avatars**: Assign different voices to different users or groups
- **Multiple TTS Providers**: Support for ElevenLabs, OpenAI, Azure, AWS Polly, and Web Speech API
- **Custom Avatar Images**: Upload and manage visual avatars for each voice


## Quick Start (End Users)

### Running the Executable

1. Find the `ChatYapper.exe` file in the dist folder
2. **Run** the executable - it will:
   - Start a local web server
   - Automatically open your browser to the settings page
   - Create necessary directories and files
3. **Configure** your settings (see Configuration section below)
4. **Connect** to Twitch and start using!

> **Important**: Keep the console window open while using Chat Yapper. Closing it will stop the application.

### First-Time Setup

1. **Twitch Connection**: Enter your Twitch channel name in settings
2. **Voice Provider**: Choose and configure at least one TTS provider
3. **Add Voices**: Create voice profiles for different users or groups

## Development Setup

### Prerequisites

- **Python 3.9+** with pip
- **Node.js 16+** with npm
- **Git** for version control

### Installation

```bash
# Clone the repository
git clone https://github.com/pladisdev/chat-yapper.git
cd chat-yapper

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### Development Workflow


#### 1. Access Development Interface

- **Frontend Dev Server**: http://localhost:5173 (with hot reload)
- **Backend API**: http://localhost:8000 (with auto-reload)
- **Backend Docs**: http://localhost:8000/docs (FastAPI Swagger UI)

### Building for Distribution

```bash
# Build everything (frontend + executable)
python build.py

# Output: dist/ChatYapper.exe
```

The build process:
1. Builds the React frontend (`npm run build`)
2. Copies build to `backend/public/`
3. Creates Windows executable with PyInstaller
4. Bundles all dependencies into single .exe file

## Configuration Guide

### Twitch Settings

| Setting | Description | Required |
|---------|-------------|----------|
| **Channel Name** | Your Twitch channel name (without #) | Yes |
| **Enable Chat** | Toggle Twitch chat reading on/off | Yes |

### TTS Provider Configuration

#### AWS Polly
- **AWS Native**: Amazon's text-to-speech service
- **Credentials**: AWS Access Key ID and Secret Access Key
- **Region**: AWS region (e.g., us-east-1)
- **Setup**:
  1. Create AWS account
  2. Create IAM user with Polly access
  3. Generate access keys for the user

#### Web Speech API (Browser)
- **Free**: Uses your browser's built-in TTS
- **No Setup**: Works immediately, no API keys needed
- **Quality**: Varies by browser and system
- **Limitations**: Only works when browser is open

### Voice Management

#### Adding Voices

1. **Go to Settings** → Voices tab
2. **Click "Add Voice"**
3. **Configure**:
   - **Name**: Display name for the voice
   - **Provider**: Choose TTS provider
   - **Voice ID**: Specific voice from provider
   - **Speed**: Speech rate (0.5-2.0)
   - **Pitch**: Voice pitch adjustment
   - **Volume**: Voice volume level

#### Voice Assignment Modes

- **Random**: Randomly assigns voices to new users
- **Sequential**: Cycles through voices in order
- **User-Specific**: Manually assign voices to specific Twitch users
- **Default**: Uses one voice for all messages

#### Avatar Images

- **Upload**: Custom images for each voice (PNG, JPG, GIF)
- **Size Limit**: 5MB maximum per image
- **Grouping**: Organize avatars into themed groups
- **Management**: Edit, delete, or reorganize avatars

## 📁 Project Structure

```
chat-yapper/
├── main.py                 # Application launcher
├── build.py               # Build script for executable
├── requirements.txt       # Python dependencies
├── logs/                  # Application logs
├── backend/               # FastAPI backend
│   ├── app.py            # Main API server
│   ├── models.py         # Database models
│   ├── tts.py            # TTS provider implementations
│   ├── twitch_listener.py # Twitch chat integration
│   ├── run_dev.py        # Development server
│   └── public/           # Built frontend files
├── frontend/             # React frontend
│   ├── src/
│   │   ├── pages/        # React components
│   │   └── websocket-manager.js
│   ├── package.json
│   └── vite.config.js
└── testing/              # Development testing tools
```

## 🔧 API Reference

### Settings Endpoints
- `GET /api/settings` - Get current settings
- `POST /api/settings` - Update settings

### Voice Management
- `GET /api/voices` - List all voices
- `POST /api/voices` - Add new voice
- `PUT /api/voices/{id}` - Update voice
- `DELETE /api/voices/{id}` - Delete voice

### Avatar Management
- `GET /api/avatars` - List available avatars
- `POST /api/avatars/upload` - Upload new avatar
- `DELETE /api/avatars/{id}` - Delete avatar

### System
- `GET /api/status` - System status and stats
- `POST /api/test` - Test TTS functionality

### WebSocket
- `WS /ws` - Real-time communication for chat messages

## 🐛 Troubleshooting

### To be added

### Log Files

- `logs/chatyapper_*.log` - Main application logs
- `logs/backend_*.log` - Backend/API logs  
- `logs/build_*.log` - Build process logs

## 📊 Changelog

### v1.0.0 (Latest)
- ✅ Initial release with full TTS functionality
- ✅ Multi-provider TTS support
- ✅ Voice avatar system
- ✅ Web-based configuration interface
- ✅ Windows executable distribution
- ✅ Comprehensive logging system

---

**Made with ❤️ for the streaming community**

For support, questions, or feature requests, please open an issue on GitHub.
