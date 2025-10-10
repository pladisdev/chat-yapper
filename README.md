# Chat Yapper

**Voice Avatar TTS System for Twitch Chat**

Chat Yapper is a text-to-speech application that reads Twitch chat messages aloud using avatars. 

## Features
- **Voice Avatars**: Assign different voices to different users or groups
- **Multiple TTS Providers**: Support for Edge, Google, Amazon, Monster
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

### v1.0.0 (Latest)
- ✅ Initial release with full TTS functionality
- ✅ Multi-provider TTS support
- ✅ Voice avatar system
- ✅ Web-based configuration interface
- ✅ Windows executable distribution
- ✅ Comprehensive logging system

---

**Made with ❤️ for the streaming community**

For support, questions, or feature requests, please open an issue on GitHub or email Pladis at pladisdev@gmail.com.