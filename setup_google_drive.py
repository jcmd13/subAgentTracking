#!/usr/bin/env python3
"""
Google Drive Setup Script for SubAgent Tracking System

One-time setup script to configure Google Drive OAuth 2.0 authentication.
Run this once to enable cloud backup functionality.

Usage:
    python setup_google_drive.py

What this script does:
1. Checks for Google Drive API credentials
2. Opens browser for OAuth consent
3. Saves authentication token
4. Verifies connection to Google Drive
5. Creates SubAgentTracking folder structure

Prerequisites:
- Google Cloud project with Drive API enabled
- OAuth 2.0 credentials downloaded as JSON
- Place credentials at: .claude/credentials/google_drive_credentials.json

For detailed setup instructions, see: docs/GOOGLE_DRIVE_SETUP.md
"""

import sys
import pickle
from pathlib import Path

# Check for Google Drive API dependencies
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("❌ Error: Google Drive API libraries not installed")
    print()
    print("Please install required packages:")
    print("  pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    print()
    sys.exit(1)

# OAuth 2.0 scopes
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Default paths
PROJECT_ROOT = Path(__file__).parent
CREDENTIALS_DIR = PROJECT_ROOT / ".claude" / "credentials"
CREDENTIALS_FILE = CREDENTIALS_DIR / "google_drive_credentials.json"
TOKEN_FILE = CREDENTIALS_DIR / "google_drive_token.pickle"


def print_header():
    """Print setup script header."""
    print("=" * 70)
    print("  SubAgent Tracking System - Google Drive Setup")
    print("=" * 70)
    print()


def check_credentials_file() -> bool:
    """
    Check if credentials file exists.

    Returns:
        True if credentials file exists, False otherwise
    """
    if CREDENTIALS_FILE.exists():
        print(f"✅ Credentials file found: {CREDENTIALS_FILE}")
        return True
    else:
        print(f"❌ Credentials file not found: {CREDENTIALS_FILE}")
        print()
        print("📝 To get Google Drive credentials:")
        print()
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Create a new project (or select existing)")
        print("3. Enable Google Drive API")
        print("4. Create OAuth 2.0 credentials (Desktop app)")
        print("5. Download credentials as JSON")
        print(f"6. Save to: {CREDENTIALS_FILE}")
        print()
        print("For detailed instructions, see: docs/GOOGLE_DRIVE_SETUP.md")
        print()
        return False


def run_oauth_flow() -> Credentials:
    """
    Run OAuth 2.0 flow to get user authorization.

    Returns:
        Credentials object with access token

    Raises:
        Exception if OAuth flow fails
    """
    print()
    print("🔐 Starting OAuth 2.0 authorization flow...")
    print()
    print("A browser window will open for you to:")
    print("  1. Sign in to your Google account")
    print("  2. Approve access to Google Drive")
    print("  3. Complete authorization")
    print()

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE),
            SCOPES
        )

        # Run local server on random port
        credentials = flow.run_local_server(port=0)

        print()
        print("✅ Authorization successful!")
        return credentials

    except Exception as e:
        print()
        print(f"❌ OAuth flow failed: {e}")
        raise


def save_token(credentials: Credentials) -> bool:
    """
    Save credentials token for future use.

    Args:
        credentials: Credentials object to save

    Returns:
        True if save successful, False otherwise
    """
    try:
        # Ensure credentials directory exists
        CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)

        # Save token
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(credentials, token)

        print(f"✅ Token saved to: {TOKEN_FILE}")
        return True

    except Exception as e:
        print(f"❌ Failed to save token: {e}")
        return False


def test_connection(credentials: Credentials) -> bool:
    """
    Test connection to Google Drive API.

    Args:
        credentials: Credentials to test

    Returns:
        True if connection successful, False otherwise
    """
    print()
    print("🔍 Testing connection to Google Drive...")

    try:
        # Build Drive service
        service = build('drive', 'v3', credentials=credentials)

        # Test API call - get user info
        about = service.about().get(fields="user").execute()
        user_email = about.get('user', {}).get('emailAddress', 'Unknown')

        print(f"✅ Connected to Google Drive as: {user_email}")

        # Try to list files (just to verify permissions)
        results = service.files().list(pageSize=1, fields="files(id, name)").execute()

        print("✅ Google Drive API permissions verified")
        return True

    except HttpError as e:
        print(f"❌ API error: {e}")
        return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False


def create_tracking_folder(credentials: Credentials) -> bool:
    """
    Create SubAgentTracking folder in Google Drive.

    Args:
        credentials: Credentials to use

    Returns:
        True if folder created/exists, False otherwise
    """
    print()
    print("📁 Creating SubAgentTracking folder structure...")

    try:
        service = build('drive', 'v3', credentials=credentials)

        # Check if folder already exists
        query = "name='SubAgentTracking' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        folders = results.get('files', [])

        if folders:
            folder_id = folders[0]['id']
            print(f"✅ SubAgentTracking folder already exists (ID: {folder_id})")
        else:
            # Create folder
            file_metadata = {
                'name': 'SubAgentTracking',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=file_metadata, fields='id').execute()
            folder_id = folder.get('id')
            print(f"✅ Created SubAgentTracking folder (ID: {folder_id})")

        return True

    except Exception as e:
        print(f"❌ Failed to create folder: {e}")
        return False


def print_success():
    """Print success message and next steps."""
    print()
    print("=" * 70)
    print("  ✅ Setup Complete!")
    print("=" * 70)
    print()
    print("Google Drive backup is now configured for SubAgent Tracking System.")
    print()
    print("📝 Next steps:")
    print()
    print("1. Backups will happen automatically on session transitions")
    print("2. You can manually backup anytime:")
    print()
    print("   from src.core.backup_manager import BackupManager")
    print("   manager = BackupManager()")
    print("   manager.backup_session()")
    print()
    print("3. View your backups on Google Drive:")
    print("   https://drive.google.com/drive/folders/")
    print()
    print("4. To restore a session:")
    print()
    print("   manager.restore_session('session_20251104_120000')")
    print()
    print("For more information, see: docs/GOOGLE_DRIVE_SETUP.md")
    print()


def main():
    """Main setup flow."""
    print_header()

    # Step 1: Check credentials file
    if not check_credentials_file():
        sys.exit(1)

    # Step 2: Run OAuth flow
    try:
        credentials = run_oauth_flow()
    except Exception:
        sys.exit(1)

    # Step 3: Save token
    if not save_token(credentials):
        sys.exit(1)

    # Step 4: Test connection
    if not test_connection(credentials):
        print()
        print("⚠️  Warning: Connection test failed")
        print("Token was saved, but you may need to re-run setup")
        sys.exit(1)

    # Step 5: Create folder structure
    if not create_tracking_folder(credentials):
        print()
        print("⚠️  Warning: Failed to create folder structure")
        print("Backups will still work, folder will be created on first backup")

    # Success!
    print_success()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        print()
        print("❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print()
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
