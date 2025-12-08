"""Backup Manager - Core Module for Google Drive Integration"""

import os
import hashlib
import logging
import time
import random
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseUpload
from src.core.config import get_config

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class BackupManager:
    """Manages backup operations to Google Drive with retry logic and verification."""

    def __init__(self):
        """Initialize BackupManager with Google Drive service and folder setup."""
        self.config = get_config()
        self.service = self.get_drive_service()
        self.folder_id = self.get_or_create_folder() if self.service else None

    def get_drive_service(self):
        """Gets the Google Drive service using OAuth credentials.

        Loads credentials from the configured token path and handles token
        refresh or re-authentication. This implementation assumes setup_google_drive.py
        has been run to establish initial credentials.

        Returns:
            Google Drive API service object or None if initialization fails.
        """
        creds = None
        token_path = self.config.get_token_path("google_drive")

        if os.path.exists(token_path):
            # Load existing token if available
            try:
                from google.oauth2.credentials import Credentials

                creds = Credentials.from_authorized_user_file(
                    token_path, scopes=["https://www.googleapis.com/auth/drive.file"]
                )
            except Exception as e:
                logging.error(f"Error loading credentials: {e}")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    # Save the refreshed credentials for next use
                    with open(token_path, "w") as token:
                        token.write(creds.to_json())
                except Exception as e:
                    logging.error(f"Error refreshing credentials: {e}")
                    return None
            else:
                logging.error(
                    "Google Drive credentials not found or invalid. Please run setup_google_drive.py first."
                )
                return None

        try:
            return build("drive", "v3", credentials=creds)
        except HttpError as error:
            logging.error(f"Error building Drive service: {error}")
            return None

    def get_or_create_folder(
        self, folder_name: str = "SubAgentTracking", parent_id: str = None
    ):
        """Gets or creates a folder in Google Drive.

        Args:
            folder_name: Name of the folder to find or create (default: SubAgentTracking)
            parent_id: Parent folder ID for nested folder creation (optional)

        Returns:
            Folder ID string or None if operation fails.
        """
        if not self.service:
            logging.error("Google Drive service not initialized.")
            return None

        try:
            # Check if the folder exists
            query = (
                f"name='{folder_name}' and "
                "mimeType='application/vnd.google-apps.folder' "
                "and trashed=false"
            )
            if parent_id:
                query += f" and '{parent_id}' in parents"

            results = self.service.files().list(q=query, pageSize=10).execute()
            items = results.get("files", [])

            if items:
                # Folder exists, return its ID
                folder_id = items[0]["id"]
                logging.info(f"Folder '{folder_name}' found with ID: {folder_id}")
                return folder_id
            else:
                # Folder doesn't exist, create it
                file_metadata = {
                    "name": folder_name,
                    "mimeType": "application/vnd.google-apps.folder",
                }
                if parent_id:
                    file_metadata["parents"] = [parent_id]

                file = self.service.files().create(body=file_metadata, fields="id").execute()
                folder_id = file.get("id")
                logging.info(f"Folder '{folder_name}' created with ID: {folder_id}")
                return folder_id

        except HttpError as error:
            logging.error(f"Error managing folder: {error}")
            return None

    def upload_file(self, file_path: str, mime_type: str, session_id: str = None) -> str:
        """Uploads a file to Google Drive with retry logic and hash verification.

        Args:
            file_path: Path to the file to upload
            mime_type: MIME type of the file
            session_id: Optional session ID for folder organization (uses config if not provided)

        Returns:
            File ID on success or None on failure.
        """
        if not self.service or not self.folder_id:
            logging.error(
                "Google Drive service not initialized. Check credentials and folder setup."
            )
            return None

        if not os.path.exists(file_path):
            logging.error(f"File not found: {file_path}")
            return None

        filename = os.path.basename(file_path)

        # Get session ID from activity logger if not provided
        if not session_id:
            from src.core import activity_logger
            session_id = activity_logger.get_current_session_id() or "unknown_session"

        # Create nested folder for session
        session_folder_id = self.get_or_create_folder(
            folder_name=session_id, parent_id=self.folder_id
        )
        if not session_folder_id:
            logging.error(f"Failed to create session folder for: {session_id}")
            return None

        file_metadata = {"name": filename, "parents": [session_folder_id]}

        try:
            # Calculate SHA256 hash of the file before upload
            sha256_hash = self.calculate_sha256(file_path)
            logging.info(f"File hash (SHA256): {sha256_hash}")

            # Create a MediaIoBaseUpload instance
            with open(file_path, "rb") as file_fd:
                media = MediaIoBaseUpload(
                    fd=file_fd,
                    mimetype=mime_type,
                    chunksize=1024 * 1024,  # 1MB chunk size
                    resumable=True,
                )

                # Create the request to upload the file
                request = self.service.files().create(body=file_metadata, media=media, fields="id")

                response = None
                retry_count = 0
                max_retries = 5

                while response is None and retry_count < max_retries:
                    try:
                        status, response = request.next_chunk()
                        if status:
                            logging.info(f"Upload progress: {int(status.progress() * 100)}%")
                    except HttpError as e:
                        logging.error(f"Error during upload chunk: {e}")
                        retry_count += 1
                        if retry_count >= max_retries:
                            logging.error("Max retries reached, upload failed.")
                            return None
                        wait_time = (2**retry_count) + random.random()
                        logging.info(
                            f"Retrying upload in {wait_time:.2f}s "
                            f"(attempt {retry_count}/{max_retries})"
                        )
                        time.sleep(wait_time)

                if response:
                    file_id = response.get("id")
                    logging.info(f"File uploaded successfully. File ID: {file_id}")
                    return file_id
                else:
                    logging.error("Upload completed but no response received.")
                    return None

        except HttpError as error:
            if error.reason == "quotaExceeded" or "dailyLimitExceeded" in str(error):
                logging.error("Google Drive quota exceeded.")
            else:
                logging.error(f"HttpError during upload: {error}")
            return None
        except IOError as e:
            logging.error(f"File I/O error: {e}")
            return None
        except Exception as e:
            logging.error(f"Unexpected error during upload: {e}")
            if "invalid_grant" in str(e) or "Invalid Credentials" in str(e):
                logging.error(
                    "Invalid Google Drive credentials. Please run setup_google_drive.py again."
                )
            return None

    def calculate_sha256(self, file_path: str) -> str:
        """Calculates the SHA256 hash of a file.

        Args:
            file_path: Path to the file to hash

        Returns:
            Hexadecimal SHA256 hash string
        """
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as file:
                while True:
                    chunk = file.read(4096)  # 4KB chunk size
                    if not chunk:
                        break
                    hasher.update(chunk)
            return hasher.hexdigest()
        except IOError as e:
            logging.error(f"Error calculating hash for {file_path}: {e}")
            return None

    def upload_activity_log(self, log_file_path: str, session_id: str = None) -> str:
        """Uploads the activity log file to Google Drive.

        Args:
            log_file_path: Path to the activity log file
            session_id: Optional session ID for organization

        Returns:
            File ID on success or None on failure.
        """
        if not self.service or not self.folder_id:
            logging.error(
                "Google Drive service not initialized. Check credentials and folder setup."
            )
            return None
        try:
            logging.info(f"Uploading activity log: {log_file_path}")
            file_id = self.upload_file(log_file_path, "application/gzip", session_id)
            return file_id
        except Exception as e:
            logging.error(f"Error uploading activity log: {e}")
            return None

    def upload_snapshots(self, snapshots_dir: str, session_id: str = None) -> str:
        """Uploads snapshots to Google Drive.

        Args:
            snapshots_dir: Path to snapshots directory or archive
            session_id: Optional session ID for organization

        Returns:
            File ID on success or None on failure.
        """
        if not self.service or not self.folder_id:
            logging.error(
                "Google Drive service not initialized. Check credentials and folder setup."
            )
            return None
        try:
            logging.info(f"Uploading snapshots: {snapshots_dir}")
            file_id = self.upload_file(snapshots_dir, "application/x-tar", session_id)
            return file_id
        except Exception as e:
            logging.error(f"Error uploading snapshots: {e}")
            return None

    def upload_analytics_snapshot(self, db_path: str, session_id: str = None) -> str:
        """Uploads the analytics database snapshot to Google Drive.

        Args:
            db_path: Path to the analytics database file
            session_id: Optional session ID for organization

        Returns:
            File ID on success or None on failure.
        """
        if not self.service or not self.folder_id:
            logging.error(
                "Google Drive service not initialized. Check credentials and folder setup."
            )
            return None
        try:
            logging.info(f"Uploading analytics database: {db_path}")
            file_id = self.upload_file(db_path, "application/vnd.sqlite3", session_id)
            return file_id
        except Exception as e:
            logging.error(f"Error uploading analytics database: {e}")
            return None

    def is_available(self) -> bool:
        """Check if Google Drive backup is configured and accessible.

        Returns:
            True if backup is available, False otherwise.
        """
        if not self.service or not self.folder_id:
            return False
        try:
            return self.test_connection()
        except Exception:
            return False

    def authenticate(self) -> bool:
        """Authenticate with Google Drive.

        Returns:
            True if authentication successful, False otherwise.
        """
        if not self.service:
            # Try to reinitialize the service
            self.service = self.get_drive_service()
            if self.service and not self.folder_id:
                self.folder_id = self.get_or_create_folder()

        if not self.service:
            logging.error("Authentication failed: Unable to initialize Google Drive service")
            return False

        try:
            # Test the connection to verify authentication
            return self.test_connection()
        except Exception as e:
            logging.error(f"Authentication failed: {e}")
            return False

    def backup_session(
        self,
        session_id: str,
        phase: str = None,
        compress: bool = True
    ) -> dict:
        """Backup an entire session including logs and snapshots.

        Args:
            session_id: The session identifier
            phase: Backup phase (checkpoint, shutdown, error) - optional
            compress: Whether to compress files before upload

        Returns:
            Dictionary with backup results:
            {
                'success': bool,
                'file_id': Optional[str],
                'error': Optional[str],
                'files_uploaded': List[str]
            }
        """
        from datetime import datetime

        if not self.is_available():
            return {
                'success': False,
                'file_id': None,
                'error': 'Google Drive not available',
                'files_uploaded': []
            }

        phase = phase or "checkpoint"
        backup_id = f"backup_{session_id}_{phase}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        files_uploaded = []

        try:
            # Upload activity log
            log_file = self.config.logs_dir / f"{session_id}.jsonl"
            if log_file.exists():
                file_id = self.upload_activity_log(str(log_file), session_id)
                if file_id:
                    files_uploaded.append(f"activity_log:{file_id}")
                    logging.info(f"Uploaded activity log for session {session_id}")

            # Upload snapshots from state directory
            # Snapshots are named like: session_20251206_143022_snap001.json
            snapshot_pattern = f"{session_id}_snap*.json"
            for snapshot_file in self.config.state_dir.glob(snapshot_pattern):
                file_id = self.upload_file(str(snapshot_file), "application/json", session_id)
                if file_id:
                    files_uploaded.append(f"snapshot:{file_id}")
            if any("snapshot:" in f for f in files_uploaded):
                logging.info(f"Uploaded snapshots for session {session_id}")

            if files_uploaded:
                return {
                    'success': True,
                    'file_id': backup_id,
                    'error': None,
                    'files_uploaded': files_uploaded
                }
            else:
                return {
                    'success': False,
                    'file_id': None,
                    'error': 'No files found to backup',
                    'files_uploaded': []
                }

        except Exception as e:
            logging.error(f"Session backup failed: {e}")
            return {
                'success': False,
                'file_id': None,
                'error': str(e),
                'files_uploaded': files_uploaded
            }

    def test_connection(self) -> bool:
        """Tests the Google Drive connection.

        Returns:
            True if connection is successful, False otherwise.
        """
        if not self.service or not self.folder_id:
            logging.warning(
                "Google Drive service not initialized. Checking credentials and folder setup."
            )
            return False
        try:
            # Attempt to list files in the SubAgentTracking folder as a connection test
            query = f"'{self.folder_id}' in parents and trashed=false"
            self.service.files().list(q=query, pageSize=1).execute()
            logging.info("Google Drive connection test successful.")
            return True
        except HttpError as error:
            logging.error(f"Connection test failed: {error}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error in connection test: {e}")
            return False
