# Google Drive Setup Guide

Quick guide to set up Google Drive backup for SubAgent Tracking System.

## Prerequisites

- Python 3.10+
- Google account
- ~10 minutes

## Step 1: Install Dependencies

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

## Step 2: Get Google Drive Credentials

1. **Go to Google Cloud Console**: https://console.cloud.google.com/

2. **Create or select a project**:
   - Click "Select a project" → "New Project"
   - Name: "SubAgent Tracking" (or any name)
   - Click "Create"

3. **Enable Google Drive API**:
   - Go to "APIs & Services" → "Library"
   - Search for "Google Drive API"
   - Click "Enable"

4. **Create OAuth 2.0 Credentials**:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - Application type: "Desktop app"
   - Name: "SubAgent Tracking Desktop"
   - Click "Create"

5. **Download Credentials**:
   - Click the download icon (⬇️) next to your OAuth client
   - Save the JSON file

6. **Move Credentials to Project**:
   ```bash
   mkdir -p .claude/credentials
   mv ~/Downloads/client_secret_*.json .claude/credentials/google_drive_credentials.json
   ```

## Step 3: Run Setup Script

```bash
python setup_google_drive.py
```

The script will:
- ✅ Verify credentials file
- 🔐 Open browser for OAuth consent
- 💾 Save authentication token
- 🔍 Test connection
- 📁 Create SubAgentTracking folder on Drive

## Step 4: Verify Setup

You should see output like:

```
======================================================================
  SubAgent Tracking System - Google Drive Setup
======================================================================

✅ Credentials file found: .claude/credentials/google_drive_credentials.json

🔐 Starting OAuth 2.0 authorization flow...

A browser window will open for you to:
  1. Sign in to your Google account
  2. Approve access to Google Drive
  3. Complete authorization

✅ Authorization successful!
✅ Token saved to: .claude/credentials/google_drive_token.pickle

🔍 Testing connection to Google Drive...
✅ Connected to Google Drive as: your.email@gmail.com
✅ Google Drive API permissions verified

📁 Creating SubAgentTracking folder structure...
✅ Created SubAgentTracking folder (ID: 1a2b3c4d5e6f...)

======================================================================
  ✅ Setup Complete!
======================================================================
```

## Using Backup Feature

### Automatic Backups

Backups happen automatically on:
- Session transitions (handoff)
- Token limit warnings
- Manual triggers

### Manual Backup

```python
from src.core.backup_manager import BackupManager

manager = BackupManager()
result = manager.backup_session()
print(f"Backup complete: {result}")
```

### List Backups

```python
backups = manager.list_backups()
for backup in backups:
    print(f"{backup['name']} - {backup['created_time']}")
```

### Restore Session

```python
manager.restore_session('session_20251104_120000')
```

## Troubleshooting

### "Credentials file not found"

Make sure you placed the credentials at:
`.claude/credentials/google_drive_credentials.json`

### "OAuth flow failed"

- Check that Drive API is enabled in Google Cloud Console
- Verify OAuth consent screen is configured
- Try re-downloading credentials

### "Connection test failed"

- Check internet connection
- Verify Google account has Drive access
- Re-run setup script

### "Permission denied"

- Make sure OAuth scope includes `https://www.googleapis.com/auth/drive.file`
- Re-create OAuth credentials if needed

## Security Notes

- **Credentials are git-ignored** - `.claude/credentials/` is in `.gitignore`
- **Token is local only** - Stored in `.claude/credentials/google_drive_token.pickle`
- **Limited scope** - Only accesses files created by this app
- **Refresh tokens** - Automatically refreshed when expired

## File Structure

```
.claude/
└── credentials/
    ├── google_drive_credentials.json  (OAuth client credentials)
    └── google_drive_token.pickle      (Access/refresh tokens)
```

## Next Steps

- ✅ Backups are configured
- Check `GETTING_STARTED.md` for usage examples
- See `README.md` for project overview

## Support

For issues or questions:
- Check `TROUBLESHOOTING.md`
- Review Google Drive API docs: https://developers.google.com/drive
- File an issue on GitHub
