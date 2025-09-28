# Chat Yapper - Routing Structure

## 🗺️ Routes

- **`/` or `/yappers`** - Main overlay page with animated avatars
- **`/settings`** - Settings and configuration page

## 📁 Directory Structure

```
frontend/
├── public/
│   └── voice_avatars/          # Place avatar images here
│       ├── ava.png
│       ├── liam.png
│       └── [your-images].png   # Any PNG, JPG, GIF, WebP files
└── src/
    ├── pages/
    │   ├── YappersPage.jsx     # Main avatar overlay (/)
    │   └── SettingsPage.jsx    # Settings page (/settings)
    └── app.jsx                 # Router setup
```

## 🎯 Usage

1. **Yappers Page (`/yappers`)**: 
   - Transparent overlay for streaming
   - Shows animated avatars when TTS plays
   - Settings button in top-right corner

2. **Settings Page (`/settings`)**: 
   - Configure voices and special events
   - Twitch connection settings
   - Test TTS with simulator
   - Avatar size and spacing controls

## 🖼️ Avatar Management

- Drop any image files (PNG, JPG, GIF, WebP) into `frontend/public/voice_avatars/`
- System automatically detects and uses all available images
- Images cycle through avatar slots as needed
- No need to edit code - just add/remove image files

## 🔄 Navigation

- Use the settings button (⚙️) to go from yappers to settings
- Use the back arrow (←) to return from settings to yappers
- Direct URLs work: `http://localhost:8000/settings`
