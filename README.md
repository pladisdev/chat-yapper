# Chat Yapper

**Voice Avatar TTS System for Twitch Chat**

Chat Yapper is a text-to-speech application that reads Twitch chat messages aloud using avatars. 

## Features
- **Voice Avatars**: Assign different voices to different users or groups
- **Multiple TTS Providers**: Support for Edge, Google, Amazon, Monster
- **Custom Avatar Images**: Upload and manage visual avatars for each voice
- **Audio Filters**: Apply reverb, echo, pitch shift, and speed changes to TTS audio (requires ffmpeg)

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
- **FFmpeg** (optional, required for audio filters)
  - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
  - Linux: `sudo apt-get install ffmpeg` or equivalent
  - Mac: `brew install ffmpeg`

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
3. **Embeds Twitch credentials from .env file into executable**
4. Creates Windows executable with PyInstaller
5. Bundles all dependencies into single .exe file

**Important**: Twitch OAuth credentials from your `.env` file are permanently embedded in the executable during build time. This means:
- ✅ The .exe works on any PC without needing a separate .env file
- ✅ Users don't need to configure Twitch credentials
- ⚠️  Make sure your .env contains the correct credentials before building
- ⚠️  The executable will contain your Twitch app credentials

## Configuration Guide

### Audio Filters (Optional Feature)

Chat Yapper supports server-side audio filtering to enhance TTS audio:

**Available Filters:**
- **Reverb**: Adds room ambiance (0-100% wetness)
- **Echo**: Creates delayed repetitions (100-1000ms delay, 0-100% decay)
- **Pitch Shift**: Changes voice pitch (-12 to +12 semitones)
- **Speed Change**: Adjusts playback speed (0.5x to 2.0x)
- **Random Mode**: Applies 1-3 random filters with random intensities

**Requirements:**
- FFmpeg must be installed and available in your system PATH
- Audio filters are applied server-side after TTS synthesis
- Filtered audio duration is automatically detected for accurate timing

**Setup:**
1. Install FFmpeg (see Prerequisites section)
2. Enable audio filters in Settings > Audio Filters tab
3. Configure individual filters or use random mode
4. Test with a message to hear the results

> **Note**: If FFmpeg is not installed, audio filters will be skipped and original TTS audio will be used.

### Environment Variables (.env file)

Chat Yapper supports configuration through environment variables. Create a `.env` file in the root directory to customize:

```bash
# Twitch OAuth Configuration (recommended for OAuth setup)
TWITCH_CLIENT_ID=your_client_id_here
TWITCH_CLIENT_SECRET=your_client_secret_here

# Server Configuration (optional)
PORT=8000                    # Backend server port
HOST=0.0.0.0                 # Backend server host
DEBUG=false                  # Enable debug logging
FRONTEND_PORT=5173           # Frontend development server port

# Database Configuration (optional)
DB_PATH=custom_database.db   # Custom database file path
```

**Setting up Twitch OAuth (.env method):**
1. Copy `.env.example` to `.env`
2. Create a Twitch app at [dev.twitch.tv/console/apps](https://dev.twitch.tv/console/apps)
3. Set redirect URL to: `http://localhost:8000/auth/twitch/callback` (or use your PORT value)
4. Fill in your `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` in `.env`
5. Restart Chat Yapper and use the "Connect to Twitch" button in settings

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

## 🧪 Testing

Chat Yapper includes comprehensive automated testing for both backend and frontend.

### Quick Test Commands

```bash
# Backend tests
cd backend
pytest -v

# Frontend tests
cd frontend
npm test -- --run

# With coverage
pytest --cov=. --cov-report=html  # Backend
npm run test:coverage              # Frontend
```

### Installation Script

```bash
# Windows PowerShell
.\install-test-deps.ps1

# Linux/Mac
bash install-test-deps.sh
```

## 📊 Changelog

### v0.5.0 (Latest)
- ✅ Initial release with full TTS functionality
- ✅ Multi-provider TTS support
- ✅ Voice avatar system
- ✅ Web-based configuration interface
- ✅ Windows executable distribution
- ✅ Comprehensive logging system

---

## TODO

### Features
- Discord integration
- Youtube Integration
- Fix emote detection system
- Better placement of avatars in UI
- Instead of localhost, use DNS
- Allow mapping of voices to avatars
- Allow users to upload an avatar and preferred voice, with streamer allowing user to be added
- More audio effects
- Built in sound alert system

### Bugs
- None lmao

---

**Made with ❤️ for the streaming community**

For support, questions, or feature requests, please open an issue on GitHub or email Pladis at pladisdev@gmail.com.