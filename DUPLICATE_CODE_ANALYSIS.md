# Duplicate Code Analysis - Chat Yapper

## Summary
This document identifies duplicate functions and API calls across the Chat Yapper codebase.

## 🔴 High Priority Duplicates (Should be consolidated)

### 1. **`log_important()` function** - 3 copies
**Location:**
- `main.py` (line 53)
- `backend/app.py` (line 67)
- `build.py` (line 47)

**Code:**
```python
def log_important(message):
    """Log important messages that should appear in both console and file"""
    logger.warning(f"IMPORTANT: {message}")  # WARNING level ensures console output
```

**Recommendation:** 
Create a shared utility module `utils/logging_utils.py` and import from there.

---

### 2. **`setup_logging()` / `setup_backend_logging()` / `setup_build_logging()` functions** - 3 similar copies
**Location:**
- `main.py` (line 19) - `setup_logging()`
- `backend/app.py` (line 29) - `setup_backend_logging()`
- `build.py` (line 13) - `setup_build_logging()`

**Similarity:** All three functions:
- Create `logs/` directory
- Create timestamped log files
- Set up file and console handlers
- Configure logging levels

**Differences:**
- Filename patterns: `chatyapper_*.log`, `backend_*.log`, `build_*.log`
- Logger names: `'ChatYapper'`, `'ChatYapper.Backend'`, `'ChatYapper.Build'`

**Recommendation:**
Create a shared logging utility:
```python
# utils/logging_utils.py
def setup_logging(log_prefix="chatyapper", logger_name="ChatYapper"):
    """Shared logging setup"""
    # ... common implementation
```

---

### 3. **`send_message()` function** - 5 copies in testing scripts
**Location:**
- `testing/quick_test.py` (line 7) - synchronous with requests
- `testing/quick_sim.py` (line 42) - async with aiohttp
- `testing/quick_capacity_test.py` (line 12) - synchronous with requests
- `testing/demo_per_user_queuing.py` (line 15) - async with aiohttp
- `testing/simulate_chat.py` (line 130) - async method in class

**Code examples:**
```python
# Synchronous version (quick_test.py, quick_capacity_test.py)
def send_message(user, text):
    data = {'user': user, 'text': text, 'eventType': 'chat'}
    response = requests.post('http://localhost:8000/api/simulate', data=data)
    return response

# Async version (quick_sim.py, demo_per_user_queuing.py)
async def send_message(session, username, message, event_type="chat"):
    data = aiohttp.FormData()
    data.add_field('user', username)
    data.add_field('text', message)
    data.add_field('eventType', event_type)
    async with session.post(f"{API_BASE_URL}/api/simulate", data=data) as response:
        return await response.json()
```

**Recommendation:**
Create a shared testing utility module:
```python
# testing/test_utils.py
class ChatYapperTestClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def send_message(self, user, text, event_type="chat"):
        """Synchronous message send"""
        pass
    
    async def send_message_async(self, session, user, text, event_type="chat"):
        """Async message send"""
        pass
```

---

## 🟡 Medium Priority Duplicates (Consider refactoring)

### 4. **API calls to `/api/settings`** - Multiple locations in frontend
**Location:**
- `SettingsPage.jsx` (line 42, 81) - GET and POST
- `YappersPage.jsx` (line 20, 555) - GET (duplicate in same file!)
- `VoiceManager.jsx` (line 33) - GET

**Pattern:**
```javascript
// GET settings
fetch(`${apiUrl}/api/settings`).then(r => r.json()).then(data => { ... })

// POST settings
await fetch(`${apiUrl}/api/settings`, { 
    method: 'POST', 
    headers: {'Content-Type': 'application/json'}, 
    body: JSON.stringify(data) 
})
```

**Recommendation:**
Create an API client utility:
```javascript
// frontend/src/api/client.js
export const api = {
    getSettings: async (apiUrl) => {
        const response = await fetch(`${apiUrl}/api/settings`)
        return response.json()
    },
    
    saveSettings: async (apiUrl, settings) => {
        const response = await fetch(`${apiUrl}/api/settings`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(settings)
        })
        return response.json()
    },
    
    // ... other API methods
}
```

---

### 5. **API calls to `/api/avatars/managed`** - Multiple locations in frontend
**Location:**
- `SettingsPage.jsx` (line 52, 154, 183, 208) - 4 times!
- `YappersPage.jsx` (line 59, 577) - 2 times

**Pattern:**
```javascript
const response = await fetch(`${apiUrl}/api/avatars/managed`)
const data = await response.json()
```

**Recommendation:**
Add to API client:
```javascript
getManagedAvatars: async (apiUrl) => {
    const response = await fetch(`${apiUrl}/api/avatars/managed`)
    return response.json()
}
```

---

### 6. **API calls to `/api/voices`** - Multiple locations in frontend
**Location:**
- `SettingsPage.jsx` (line 47) - GET
- `YappersPage.jsx` (line 155) - GET
- `VoiceManager.jsx` (line 22, 174, 192, 207) - GET, POST, DELETE

**Recommendation:**
Add to API client for centralized voice management API calls.

---

## 🟢 Low Priority (Acceptable duplicates)

### 7. **Static file serving routes** - Multiple similar routes
**Location:** `backend/app.py`
- Line 1582: `/settings` route
- Line 1587: `/yappers` route
- Line 1606: `/` (root) route

**Code:**
```python
@app.get("/settings")
async def serve_settings():
    """Serve settings page"""
    index_path = os.path.join(PUBLIC_DIR, "index.html")
    return FileResponse(index_path, media_type='text/html')

@app.get("/yappers")
async def serve_yappers():
    """Serve yappers page"""
    index_path = os.path.join(PUBLIC_DIR, "index.html")
    return FileResponse(index_path, media_type='text/html')
```

**Recommendation:**
Keep as-is for clarity, OR create a helper:
```python
def serve_spa_route(route_name: str):
    """Helper to serve SPA routes"""
    async def serve():
        index_path = os.path.join(PUBLIC_DIR, "index.html")
        return FileResponse(index_path, media_type='text/html')
    serve.__name__ = f"serve_{route_name}"
    serve.__doc__ = f"Serve {route_name} page"
    return serve

@app.get("/settings")
async def serve_settings():
    return await serve_spa_route("settings")()
```

---

### 8. **`activeAudioRef.current.get()` calls** - YappersPage.jsx
**Location:**
- Line 471, 493, 653, 714

**Pattern:**
```javascript
const userAudio = activeAudioRef.current.get(msg.user?.toLowerCase())
```

**Recommendation:**
Keep as-is - these are legitimate uses in different contexts (user audio management).

---

## 📊 Statistics

| Category | Count | Files Affected |
|----------|-------|----------------|
| Logging utilities | 3 | main.py, backend/app.py, build.py |
| Testing utilities | 5 | testing/*.py |
| Frontend API calls (settings) | 5 | 3 components |
| Frontend API calls (avatars) | 6 | 2 components |
| Frontend API calls (voices) | 5 | 2 components |
| Backend SPA routes | 3 | backend/app.py |

---

## 🛠️ Recommended Refactoring Plan

### Phase 1: Shared Utilities (High Priority)
1. Create `utils/logging_utils.py` with shared logging functions
2. Update `main.py`, `backend/app.py`, and `build.py` to use shared utilities
3. Create `testing/test_utils.py` with shared test helper functions
4. Update all testing scripts to use shared utilities

### Phase 2: Frontend API Client (Medium Priority)
1. Create `frontend/src/api/client.js` with centralized API methods
2. Update `SettingsPage.jsx` to use API client
3. Update `YappersPage.jsx` to use API client
4. Update `VoiceManager.jsx` to use API client

### Phase 3: Code Review (Optional)
1. Review backend SPA routes for potential helper function
2. Audit remaining duplicate patterns

---

## 💾 Estimated Impact

**Before:**
- ~150 lines of duplicate code across backend logging
- ~80 lines of duplicate code across testing utilities
- ~100+ duplicate fetch calls in frontend

**After:**
- Single source of truth for logging (~50 lines)
- Single source of truth for testing (~100 lines)
- Centralized API client (~200 lines)
- Easier maintenance and bug fixes
- Reduced bundle size in frontend

---

## 📝 Notes

### Not Duplicates (False Positives)
The following patterns appear multiple times but are NOT duplicates:

1. **Backend API endpoints** - Each endpoint is unique and serves different purposes
2. **Database model fields** - Repetitive but necessary schema definitions
3. **Form data creation in testing** - Slight variations in implementation for different test scenarios
4. **WebSocket message handling** - Different message types require different handling logic

### Testing Script Consolidation
The 5 testing scripts have different purposes:
- `quick_test.py` - Simple manual testing
- `quick_sim.py` - Complex simulation with multiple users
- `quick_capacity_test.py` - Avatar capacity stress testing
- `demo_per_user_queuing.py` - Per-user queuing demonstration
- `simulate_chat.py` - Full chat simulation class

**Recommendation:** Keep separate scripts but extract common utilities to `test_utils.py`

---

## ✅ Action Items

- [ ] Create `utils/logging_utils.py` module
- [ ] Refactor logging in main.py, app.py, build.py
- [ ] Create `testing/test_utils.py` module
- [ ] Refactor testing scripts to use shared utilities
- [ ] Create `frontend/src/api/client.js`
- [ ] Refactor frontend components to use API client
- [ ] Add tests for new utility modules
- [ ] Update documentation
