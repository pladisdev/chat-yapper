# Testing Quick Reference

## ⚡ Quick Commands

### Backend Tests
```powershell
cd backend
pytest -v                              # Run all tests
pytest -v --cov=. --cov-report=html   # With coverage HTML report
pytest -m unit                         # Only unit tests
pytest tests/test_models.py           # Specific file
```

### Frontend Tests
```powershell
cd frontend
npm test                               # Watch mode
npm test -- --run                      # Run once
npm run test:coverage                  # With coverage
npm run test:ui                        # UI mode
```

## 📊 Coverage Reports

### Backend
After running with `--cov-report=html`, open: `backend/htmlcov/index.html`

### Frontend
After running `npm run test:coverage`, open: `frontend/coverage/index.html`

## 🏷️ Test Markers (Backend)

- `pytest -m unit` - Unit tests only
- `pytest -m integration` - Integration tests
- `pytest -m api` - API endpoint tests
- `pytest -m tts` - TTS functionality tests
- `pytest -m "not slow"` - Skip slow tests

## 🔧 Install Test Dependencies

```powershell
# Windows
.\install-test-deps.ps1

# Or manually:
cd backend
pip install pytest pytest-asyncio pytest-cov httpx
cd ../frontend
npm install
```

## ✅ CI/CD Status

- GitHub Actions runs tests automatically on push/PR
- Tests run on Python 3.9, 3.10, 3.11 and Node 18.x, 20.x
- View results: Repository → Actions tab

## 📚 Full Documentation

- **TESTING.md** - Complete testing guide
- **CI_FIXES_APPLIED.md** - Recent CI/CD fixes
- **TESTING_SETUP_COMPLETE.md** - Setup overview

## 🐛 Troubleshooting

**Tests not found?**
```powershell
# Make sure you're in the right directory
cd backend  # or cd frontend
```

**Import errors?**
```powershell
# Install dependencies
pip install -r requirements.txt    # Backend
npm install                        # Frontend
```

**Coverage not working?**
```powershell
# Backend: Install pytest-cov
pip install pytest-cov

# Frontend: Already included in package.json
npm install
```

---

**Need help?** See TESTING.md for detailed documentation.
