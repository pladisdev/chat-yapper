# GitHub Actions Build and Release Setup

This repository is configured to automatically build Windows executables and create releases when merging to `main`.

## 🔄 Workflow Overview

### For Pull Requests to `main`:
1. **Automatic Build**: When you create or update a PR to merge `develop` → `main`, the workflow will:
   - Build the frontend (React/Vite)
   - Build the Windows executable using `deployment/build.py`
   - Run validation tests
   - Upload the executable as an artifact
   - Comment on the PR with build status

2. **Build Verification**: The PR **cannot be merged** if:
   - The build fails
   - The executable is not created
   - Any validation tests fail

### After Merging to `main`:
1. **Automatic Release**: When the PR is merged, the workflow will:
   - Create a new GitHub Release with version tag (format: `vYYYY.MM.DD-shortsha`)
   - Upload `ChatYapper.exe` to the release
   - Generate release notes automatically

## ⚙️ Setup Instructions

### 1. Commit and Push the Workflow (First!)

The status checks won't exist until the workflow runs at least once:

```bash
git add .github/
git commit -m "Add automated build and release workflow"
git push origin develop
```

### 2. Create a Test PR (To Register Status Checks)

Create a Pull Request from `develop` → `main` to trigger the workflow.

**Don't merge it yet!** Just let it run so GitHub registers the status check names.

### 3. Configure Branch Protection Rules

**After the workflow has run**, go to **Settings → Branches → Add branch protection rule** for `main`:

**Required settings:**
- [x] Require a pull request before merging
- [x] Require status checks to pass before merging
  - Add required check: `Build Status Check`
  - Add required check: `Build Windows Executable`
- [x] Require branches to be up to date before merging
- [x] Do not allow bypassing the above settings

**Important**: These status check names will only appear in the search dropdown after the workflow has run successfully at least once.

This ensures that:
- All code must go through a PR
- Build must succeed before merge
- No direct pushes to `main`

### 2. Add GitHub Secrets (Optional)

If your application uses Twitch OAuth, add these secrets:

Go to **Settings → Secrets and variables → Actions → New repository secret**:

- `TWITCH_CLIENT_ID`: Your Twitch application client ID
- `TWITCH_CLIENT_SECRET`: Your Twitch application client secret

These secrets are embedded in the executable at build time. If not provided, the build will still succeed but Twitch features may not work.

### 3. Enable GitHub Actions

Make sure GitHub Actions are enabled:
- Go to **Settings → Actions → General**
- Set "Actions permissions" to "Allow all actions and reusable workflows"
- Under "Workflow permissions", select "Read and write permissions"

## 📋 Workflow File

The workflow is defined in `.github/workflows/build-and-release.yml`

**Key features:**
- Runs on Windows (required for `.exe` build)
- Uses Python 3.11 and Node.js 20
- Caches dependencies for faster builds
- Creates date-based version tags
- Uploads artifacts for PR testing
- Auto-creates releases on merge

## 🚀 Usage

### Normal Development Flow:
```bash
# Work on develop branch
git checkout develop
git add .
git commit -m "Add new feature"
git push origin develop

# Create PR: develop → main
# GitHub UI: Create Pull Request

# Wait for build to complete
# If successful, merge PR
# Release is created automatically!
```

### Manual Workflow Dispatch:
You can also trigger builds manually:
1. Go to **Actions** tab
2. Select "Build and Release" workflow
3. Click "Run workflow"
4. Choose branch

## 📦 Build Artifacts

### For Pull Requests:
- Executable is uploaded as a workflow artifact
- Available for 7 days
- Download from the workflow run page to test

### For Merged Commits:
- Executable is attached to the GitHub Release
- Available permanently
- Downloadable from the Releases page

## 🛠️ Troubleshooting

### Build fails with "Executable not found"
- Check the build logs for Python/Node errors
- Ensure `deployment/build.py` completes successfully
- Verify frontend builds correctly

### Cannot merge PR
- Ensure "Build Status Check" passes
- Check branch protection rules are not too strict
- Verify workflow has write permissions

### Release not created after merge
- Check that the merge was to `main` branch
- Verify GitHub Actions has write permissions
- Look for errors in the workflow run

## 🔐 Security Notes

- Secrets are only available to the workflow, not in logs
- `.env` file is created temporarily and not committed
- Executable contains embedded secrets (if provided)
- Artifacts are only visible to repository collaborators

## 📝 Version Format

Releases are automatically tagged with:
```
vYYYY.MM.DD-shortsha
```

Example: `v2025.10.14-a1b2c3d`

Where:
- `YYYY.MM.DD` = Build date
- `shortsha` = First 7 characters of the commit hash

## 🎯 Next Steps

1. ✅ Commit this workflow file
2. ✅ Configure branch protection for `main`
3. ✅ Add GitHub secrets (if needed)
4. ✅ Test with a PR from `develop` to `main`
5. ✅ Verify build succeeds and blocks merge if it fails
6. ✅ Merge and verify release is created

---

**Note**: The first build may take longer as GitHub Actions sets up the environment and caches dependencies. Subsequent builds will be faster.
