# Quick Reference: Build & Release Workflow

## ✅ What's Been Set Up

1. **Workflow File**: `.github/workflows/build-and-release.yml`
   - Automatically builds on PR to `main`
   - Creates release on merge to `main`
   - Fails merge if build fails

2. **Documentation**: `.github/BUILD_AND_RELEASE.md`
   - Complete setup guide
   - Troubleshooting tips
   - Security notes

## 🎯 What You Need To Do

### Step 1: Commit and Push Workflow Files (Do This First!)
```bash
git add .github/ QUICK_START_BUILD_RELEASE.md
git commit -m "Add automated build and release workflow"
git push origin development
```

### Step 2: Create a Test PR (To Generate Status Checks)
Create a PR from `development` → `main` to trigger the workflow for the first time.

**Important**: Don't merge it yet! Just let it run so GitHub registers the status checks.

### Step 3: Configure Branch Protection (After Workflow Runs)
Go to: **GitHub → Settings → Branches**

1. Click "Add branch protection rule"
2. Branch name pattern: `main`
3. Enable these settings:
   - ✅ Require a pull request before merging
   - ✅ Require status checks to pass before merging
     - Search and add: `Build Status Check`
     - Search and add: `Build Windows Executable`
   - ✅ Require branches to be up to date before merging
4. Click "Create" or "Save changes"

**Note**: The status checks will only appear in the search after the workflow has run at least once!

### Step 2: Add Secrets (Optional)
Only needed if you use Twitch OAuth features.

Go to: **GitHub → Settings → Secrets and variables → Actions**

Add these secrets:
- `TWITCH_CLIENT_ID` = your Twitch client ID
- `TWITCH_CLIENT_SECRET` = your Twitch client secret

### Step 3: Enable Actions Permissions
Go to: **GitHub → Settings → Actions → General**

Set:
- Actions permissions: "Allow all actions and reusable workflows"
- Workflow permissions: "Read and write permissions"
- ✅ Check "Allow GitHub Actions to create and approve pull requests"

### Step 4: Close Test PR and Create Real One
After the workflow runs and you've configured branch protection:

1. Close the test PR (don't merge)
2. Create a new PR from `development` → `main`
3. Now branch protection will enforce the checks!
4. Merge when ready → automatic release! 🎉

## 📋 How It Works

### When you create a PR (develop → main):
✅ Builds the executable  
✅ Runs tests  
✅ Uploads artifact  
✅ Comments on PR with status  
❌ **Blocks merge if build fails**

### When you merge the PR:
✅ Creates a GitHub Release  
✅ Tags with version (e.g., `v2025.10.14-a1b2c3d`)  
✅ Uploads `ChatYapper.exe` to the release  
✅ Generates release notes

## 🚨 Important Notes

- **First build takes ~10-15 minutes** (caching dependencies)
- **Subsequent builds take ~5-7 minutes** (cached)
- **Merge is blocked if build fails** (this is what you wanted!)
- **Releases are automatic** (no manual steps needed)

## 🎉 Benefits

1. ✅ Can't accidentally merge broken code
2. ✅ Always have a working executable
3. ✅ Automatic versioning
4. ✅ Test executable before merging (via artifact)
5. ✅ Instant releases on merge

## 🔍 Where to Find Things

**Check build status:**
- GitHub → Pull Requests → Your PR → "Checks" tab

**Download test artifact:**
- GitHub → Actions → Click the workflow run → Scroll to "Artifacts"

**View releases:**
- GitHub → Releases (right sidebar)
- Or: `https://github.com/pladisdev/chat-yapper/releases`

## 💡 Pro Tips

1. **Test locally first**: Run `python build.py` before pushing
2. **Check logs**: If build fails, click on the failed check for details
3. **Draft releases**: Modify workflow to create draft releases if you want to review first
4. **Custom versions**: Edit the version format in the workflow if needed

---

Ready to go! Commit these files and configure the branch protection. 🚀
