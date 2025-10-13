# 🚀 Setup Steps (In Order!)

## The Problem You Just Hit
GitHub doesn't know what status checks exist until the workflow runs for the first time. So you need to:
1. Push the workflow
2. Run it once
3. **Then** configure branch protection

## ✅ Correct Setup Order

### 1️⃣ Commit and Push (Right Now)
```bash
git add .github/ QUICK_START_BUILD_RELEASE.md
git commit -m "Add automated build and release workflow"
git push origin development
```

### 2️⃣ Create a Test PR
- Go to GitHub
- Create Pull Request: `development` → `main`
- **Title**: "Test: Add build workflow"
- **Description**: "Testing automated build - DO NOT MERGE YET"
- Click "Create pull request"

### 3️⃣ Wait for Workflow to Run
- Go to the "Checks" tab on your PR
- Wait for "Build Windows Executable" to start
- It will take ~10-15 minutes for the first build
- ☕ Go get coffee!

### 4️⃣ Configure Branch Protection
**Only after the workflow has run!**

Go to: **Settings → Branches → Add branch protection rule**

Settings:
```
Branch name pattern: main

☑️ Require a pull request before merging
   ☑️ Require approvals: 0 (or 1 if you want reviews)

☑️ Require status checks to pass before merging
   ☑️ Require branches to be up to date before merging
   
   Search for status checks:
   ✅ Build Status Check
   ✅ Build Windows Executable
   
☑️ Do not allow bypassing the above settings
```

Click "Create" or "Save changes"

### 5️⃣ Close Test PR
- Go back to your test PR
- Click "Close pull request" (don't merge!)
- Add comment: "Test complete, branch protection configured"

### 6️⃣ Create Real PR
Now when you create a PR from `development` → `main`:
- ✅ Build runs automatically
- ✅ Merge button is disabled until build succeeds
- ✅ On merge, automatic release is created!

## 🎯 Why This Order?

```
❌ WRONG ORDER:
Set branch protection → No status checks exist → Error!

✅ CORRECT ORDER:
Push workflow → Run once → Status checks exist → Set branch protection → Works!
```

## 💡 Quick Test After Setup

Create a real PR and verify:
1. Build starts automatically ✅
2. Merge button says "Merging is blocked" until build finishes ✅
3. After build succeeds, merge button becomes available ✅
4. After merging, a release is created ✅

---

**Ready?** Start with Step 1️⃣ above! 🚀
