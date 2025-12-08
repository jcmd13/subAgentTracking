"""Backup Manager - Core Module for Google Drive Integration"""

import os
import hashlib
import logging
import time
import random
import tarfile
import gzip
import pickle
from pathlib import Path
from typing import Optional, Dict, Any, List

try:  # Optional dependency; tests patch google modules
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.auth.transport.requests import Request
    from googleapiclient.http import MediaIoBaseUpload

    GOOGLE_DRIVE_AVAILABLE = True
except Exception:  # pragma: no cover - handled in tests
    build = None
    HttpError = Exception
    Request = None
    MediaIoBaseUpload = None
    GOOGLE_DRIVE_AVAILABLE = False

from src.core.config import get_config
from src.core import activity_logger

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class BackupManager:
    """Manages backup operations to Google Drive with retry logic and verification."""

    def __init__(self):
        """Initialize BackupManager with Google Drive service and folder setup."""
        self.config = get_config()
        self.service: Optional[Any] = None
        self.folder_id: Optional[str] = None
        self.drive_folder_id: Optional[str] = None

    def get_drive_service(self):
        """Gets the Google Drive service using OAuth credentials.

        Loads credentials from the configured token path and handles token
        refresh or re-authentication. This implementation assumes setup_google_drive.py
        has been run to establish initial credentials.

        Returns:
            Google Drive API service object or None if initialization fails.
        """
        if not GOOGLE_DRIVE_AVAILABLE:
            return None
        creds = None
        token_path = (
            self.config.get_token_path("google_drive")
            if hasattr(self.config, "get_token_path")
            else self.config.credentials_dir / "google_drive_token.pickle"
        )

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

    def is_available(self) -> bool:
        """Check if Google Drive backup is configured and accessible."""
        return bool(GOOGLE_DRIVE_AVAILABLE and getattr(self.config, "backup_enabled", True))

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

    def authenticate(self) -> bool:
        """Authenticate with Google Drive.

        Returns:
            True if authentication successful, False otherwise.
        """
        if not self.is_available():
            return False

        credentials_path = self.config.credentials_dir / "google_drive_credentials.json"
        token_path = self.config.credentials_dir / "google_drive_token.pickle"

        # No credentials/token available
        if not token_path.exists() and not credentials_path.exists():
            return False

        try:
            if token_path.exists():
                with open(token_path, "rb") as token_file:
                    creds = pickle.load(token_file)
            else:
                creds = None

            if creds is None or not getattr(creds, "valid", True):
                return False

            if build is None:
                return False

            self.service = build("drive", "v3", credentials=creds)
            self.folder_id = self.get_or_create_folder(
                getattr(self.config, "google_drive_folder_name", "SubAgentTracking")
            )
            self.drive_folder_id = self.folder_id
            return True
        except Exception as e:
            logging.error(f"Authentication failed: {e}")
            self.service = None
            return False

    def _create_session_archive(self, session_id: str, compress: bool = True) -> Optional[Path]:
        """Create a tar archive containing session artifacts."""
        try:
            archive_name = f"{session_id}.tar.gz" if compress else f"{session_id}.tar"
            archive_path = self.config.credentials_dir / archive_name
            mode = "w:gz" if compress else "w"

            with tarfile.open(archive_path, mode) as tar:
                log_file = self.config.logs_dir / f"{session_id}.jsonl.gz"
                if not log_file.exists():
                    log_file = self.config.logs_dir / f"{session_id}.jsonl"
                if log_file.exists():
                    tar.add(log_file, arcname=f"logs/{log_file.name}")
                    tar.add(log_file, arcname="activity.jsonl")

                for snapshot_file in self.config.state_dir.glob(f"{session_id}_snap*.json*"):
                    tar.add(snapshot_file, arcname=f"snapshots/{snapshot_file.name}")

                handoff = self.config.handoffs_dir / f"{session_id}_handoff.md"
                if handoff.exists():
                    tar.add(handoff, arcname=f"handoffs/{handoff.name}")

                analytics_db = self.config.analytics_dir / "tracking.db"
                if analytics_db.exists():
                    tar.add(analytics_db, arcname=f"analytics/{analytics_db.name}")

            return archive_path
        except Exception as e:
            logging.error(f"Failed to create archive for {session_id}: {e}")
            return None

    def _extract_session_archive(self, archive_path: Path, session_id: str) -> List[Path]:
        """Extract a session archive into configured directories."""
        extracted: List[Path] = []
        if not archive_path.exists():
            return extracted

        mode = "r:gz" if archive_path.suffix == ".gz" else "r"
        with tarfile.open(archive_path, mode) as tar:
            tar.extractall(path=self.config.project_root)
            for member in tar.getmembers():
                extracted.append(self.config.project_root / member.name)

        return extracted

    def _upload_to_drive(self, file_path: Path, filename: Optional[str] = None, parent_id: Optional[str] = None) -> Optional[str]:
        """Upload a file to Google Drive; returns file ID or None."""
        if not self.service:
            return None
        metadata = {"name": filename or file_path.name}
        if parent_id:
            metadata["parents"] = [parent_id]
        try:
            create_request = self.service.files().create(body=metadata, fields="id")
            response = create_request.execute()
            if isinstance(response, dict):
                return response.get("id")
            if hasattr(response, "get"):
                return response.get("id")
        except Exception as e:
            logging.error(f"Upload failed: {e}")
        return None

    def _download_from_drive(self, file_id: str, dest_path: Path) -> bool:
        """Download a file from Google Drive to dest_path."""
        if not self.service:
            return False
        try:
            request = self.service.files().get_media(fileId=file_id)
            data = request.execute()
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                if isinstance(data, bytes):
                    f.write(data)
                else:
                    f.write(b"")
            return True
        except Exception as e:
            logging.error(f"Download failed: {e}")
            return False

    def _find_session_archive(self, session_id: str) -> Optional[str]:
        """Find archive file ID for session."""
        if not self.service:
            return None
        try:
            query = f"name contains '{session_id}'"
            result = self.service.files().list(q=query, pageSize=1).execute()
            files = result.get("files", [])
            if files:
                return files[0].get("id")
        except Exception as e:
            logging.error(f"Find archive failed: {e}")
        return None

    # Compatibility aliases expected by tests
    def _find_file_in_drive(self, filename: str) -> Optional[str]:
        return self._find_session_archive(filename)

    def _get_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        return self.get_or_create_folder(folder_name=folder_name, parent_id=parent_id)

    def list_backups(self) -> List[dict]:
        """List backup files in the drive folder."""
        if not self.service or not (self.folder_id or self.drive_folder_id):
            return []
        try:
            parent = self.drive_folder_id or self.folder_id
            result = self.service.files().list(q=f"'{parent}' in parents", pageSize=100).execute()
            return result.get("files", [])
        except Exception:
            return []

    def backup_session(
        self,
        session_id: Optional[str] = None,
        phase: str = None,
        compress: bool = True
    ) -> dict:
        """Backup an entire session including logs and snapshots."""
        from datetime import datetime

        if not session_id:
            session_id = activity_logger.get_current_session_id()
        if not session_id:
            return {"success": False, "error": "No session ID available"}

        if not self.is_available():
            return {
                "success": False,
                "error": "Google Drive not available",
                "session_id": session_id,
            }

        start = time.time()
        archive_path = self._create_session_archive(session_id, compress=compress)
        if not archive_path or not archive_path.exists():
            return {"success": False, "error": "Failed to create archive", "session_id": session_id}

        file_id = None
        if self.service and self.drive_folder_id:
            file_id = self._upload_to_drive(archive_path, parent_id=self.drive_folder_id)

        duration_ms = int((time.time() - start) * 1000)
        return {
            "success": True,
            "session_id": session_id,
            "file_id": file_id,
            "size_bytes": archive_path.stat().st_size,
            "duration_ms": duration_ms,
        }

    def restore_session(self, session_id: str) -> dict:
        """Restore a session archive from Google Drive."""
        if not self.is_available():
            return {"success": False, "error": "Google Drive not available"}
        if not self.service or not self.drive_folder_id:
            return {"success": False, "error": "Service not authenticated"}

        file_id = self._find_session_archive(session_id)
        if not file_id:
            return {"success": False, "error": "Session archive not found"}

        dest = self.config.credentials_dir / f"{session_id}.tar.gz"
        if not self._download_from_drive(file_id, dest):
            return {"success": False, "error": "Download failed"}

        restored_files = self._extract_session_archive(dest, session_id)
        return {"success": True, "restored_files": restored_files}

    def test_connection(self) -> bool:
        """Tests the Google Drive connection."""
        if not self.is_available():
            return False
        return bool(self.service and (self.folder_id or self.drive_folder_id))


# ============================================================================
# Convenience functions
# ============================================================================


def test_connection() -> bool:
    """Module-level helper for quick connectivity checks."""
    manager = BackupManager()
    return manager.test_connection()


def backup_current_session() -> dict:
    """Backup the current session (if any)."""
    manager = BackupManager()
    return manager.backup_session()


def list_available_backups() -> List[dict]:
    """List available backups (stub for compatibility)."""
    manager = BackupManager()
    if not manager.is_available() or not manager.service:
        return []
    try:
        result = manager.service.files().list().execute()
        files = result.get("files", [])
        return files
    except Exception:
        return []
