"""Backup service for database backups."""

import json
import shutil
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

from PySide6.QtCore import QObject, QSettings
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from oeapp import __version__
from oeapp.db import get_project_db_path
from oeapp.exc import BackupFailed
from oeapp.models.project import Project

if TYPE_CHECKING:
    from pathlib import Path


class BackupService(QObject):
    """
    Service for managing database backups.

    Handles creating backups, managing retention, and extracting metadata.
    """

    def __init__(self) -> None:
        """Initialize backup service."""
        super().__init__()
        self.settings = QSettings()
        self.db_path = get_project_db_path()
        self.backup_dir = self.db_path.parent / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def get_num_backups(self) -> int:
        """
        Get the number of backups to keep from settings.

        Returns:
            Number of backups to keep (default: 5)

        """
        return cast("int", self.settings.value("backup/num_backups", 5, type=int))

    def get_interval_minutes(self) -> int:
        """
        Get the backup interval in minutes from settings.

        Returns:
            Backup interval in minutes (default: 720 = 12 hours)

        """
        return cast(
            "int", self.settings.value("backup/interval_minutes", 720, type=int)
        )

    def get_last_backup_time(self) -> datetime | None:
        """
        Get the timestamp of the last backup from settings.

        Returns:
            Last backup timestamp in local time, or None if no backup has been made

        """
        last_backup_epoch = cast(
            "float | None",
            self.settings.value("backup/last_backup_time", None, type=float),
        )
        if last_backup_epoch is not None:
            # Convert from UNIX epoch (UTC) to local datetime
            return datetime.fromtimestamp(last_backup_epoch, tz=UTC)
        return None

    def set_last_backup_time(self, timestamp: datetime) -> None:
        """
        Set the timestamp of the last backup in settings.

        Stores as UNIX epoch (seconds since 1970-01-01 UTC) to avoid DST issues.

        Args:
            timestamp: Timestamp of the backup (will be converted to UTC epoch)

        """
        # Convert datetime to UNIX epoch (UTC-based)
        epoch_seconds = timestamp.timestamp()
        self.settings.setValue("backup/last_backup_time", epoch_seconds)

    def should_backup(self) -> bool:
        """
        Check if a backup is needed based on time since last backup.

        Returns:
            True if backup is needed, False otherwise

        """
        last_backup = self.get_last_backup_time()
        if last_backup is None:
            return True

        interval_minutes = self.get_interval_minutes()
        time_since_backup = (datetime.now(tz=UTC) - last_backup).total_seconds() / 60

        return time_since_backup >= interval_minutes

    def get_current_migration_version(self, engine: Engine) -> str | None:
        """
        Get the current migration version from the database.

        Args:
            engine: SQLAlchemy engine

        Returns:
            Migration version string, or None if no version is set

        """
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        if "alembic_version" not in existing_tables:
            return None

        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            )
            row = result.fetchone()
            if row:
                return row[0]
        return None

    def extract_backup_metadata(
        self, session: Session, engine: Engine
    ) -> dict[str, Any]:
        """
        Extract metadata from the database for backup.

        Args:
            session: SQLAlchemy session
            engine: SQLAlchemy engine

        Returns:
            Dictionary containing backup metadata

        """
        # Get migration version
        migration_version = self.get_current_migration_version(engine)

        # Get database file size
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

        # Get projects with token counts
        projects_data = []
        projects = Project.list(session)
        for project in projects:
            # Count tokens for this project through sentences
            total_tokens = project.total_token_count(session)
            projects_data.append(
                {
                    "id": project.id,
                    "name": project.name,
                    "last_updated": project.updated_at.isoformat(),
                    "token_count": total_tokens,
                }
            )

        return {
            "backup_timestamp": datetime.now(UTC).isoformat(),
            "database_file_size": db_size,
            "migration_version": migration_version,
            "application_version": __version__,
            "projects": projects_data,
        }

    def create_backup(self) -> Path:
        """
        Create a backup of the database immediately.

        Returns:
            Path to the created backup file, or None if backup failed

        Raises:
            BackupFailed: If the backup fails
            BackupFailed: If the database file does not exist

        """
        if not self.db_path.exists():
            raise BackupFailed(OSError("Database file does not exist"), self.db_path)

        # Generate backup filename with timestamp (UTC to avoid DST issues)
        timestamp = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M-%S")
        backup_filename = f"{self.db_path.stem}_{timestamp}.db"
        backup_path = self.backup_dir / backup_filename

        # Copy database file
        try:
            shutil.copy2(self.db_path, backup_path)
        except (OSError, PermissionError) as e:
            print(f"Failed to copy database file: {e}")  # noqa: T201
            raise BackupFailed(e, backup_path) from e

        # Create temporary engine and session to extract metadata
        temp_engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        SessionLocal = sessionmaker(bind=temp_engine)  # noqa: N806
        temp_session = SessionLocal()

        try:
            # Extract metadata (may fail if database is empty/fresh or has errors)

            try:
                metadata = self.extract_backup_metadata(temp_session, temp_engine)
            except (SQLAlchemyError, OSError) as e:
                # If metadata extraction fails, create minimal metadata
                print(f"Metadata extraction failed, using minimal metadata: {e}")  # noqa: T201
                try:
                    db_size = self.db_path.stat().st_size
                except OSError:
                    db_size = 0
                metadata = {
                    "backup_timestamp": datetime.now(UTC).isoformat(),
                    "database_file_size": db_size,
                    "migration_version": None,
                    "application_version": __version__,
                    "projects": [],
                }

            # Save metadata to JSON file
            metadata_filename = f"{self.db_path.stem}_{timestamp}.json"
            metadata_path = self.backup_dir / metadata_filename
            try:
                with metadata_path.open("w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2)
            except (OSError, PermissionError, TypeError) as e:
                raise BackupFailed(e, metadata_path) from e
                # Continue anyway - backup file was created successfully

            # Update last backup time (UTC to avoid DST issues)
            self.set_last_backup_time(datetime.now(UTC))

            # Cleanup old backups (non-critical, continue even if it fails)
            try:
                self.cleanup_old_backups()
            except OSError as e:
                print(f"Failed to cleanup old backups: {e}")  # noqa: T201
                # Continue - backup was successful

            return backup_path
        finally:
            temp_session.close()
            temp_engine.dispose()

    def cleanup_old_backups(self) -> None:
        """Remove backups beyond the retention limit."""
        num_backups = self.get_num_backups()

        # Get all backup files (both .db and .json)
        backup_files = list(self.backup_dir.glob(f"{self.db_path.stem}_*.db"))
        backup_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        # Keep only the most recent backups
        if len(backup_files) > num_backups:
            for backup_file in backup_files[num_backups:]:
                # Delete .db file
                backup_file.unlink()
                # Delete corresponding .json file
                json_file = backup_file.with_suffix(".json")
                if json_file.exists():
                    json_file.unlink()

    def get_backup_list(self) -> list[dict[str, Any]]:
        """
        Get a list of all available backups with metadata.

        Returns:
            List of dictionaries containing backup information

        """
        backups = []
        backup_files = list(self.backup_dir.glob(f"{self.db_path.stem}_*.db"))

        for backup_file in backup_files:
            # Try to load metadata from JSON file
            json_file = backup_file.with_suffix(".json")
            metadata: dict[str, Any] = {}
            if json_file.exists():
                try:
                    with json_file.open("r", encoding="utf-8") as f:
                        metadata = json.load(f)
                except (OSError, json.JSONDecodeError):
                    # Metadata file is corrupted or unreadable - continue without it
                    pass

            # Get file stats
            try:
                stat = backup_file.stat()
                file_size = stat.st_size
                # st_mtime is a Unix timestamp (UTC-based), convert to UTC datetime
                file_time = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
            except OSError:
                # Skip this backup file if we can't read its stats
                continue

            # Extract timestamp from metadata (stored in UTC)
            backup_timestamp = metadata.get("backup_timestamp")
            if backup_timestamp:
                try:
                    # Parse ISO format timestamp (may be UTC with timezone info)
                    file_time = datetime.fromisoformat(backup_timestamp).replace(
                        tzinfo=UTC
                    )
                    # If timezone-aware, keep it as-is (will be converted to
                    # local in UI) If naive, treat as UTC (for backwards
                    # compatibility with old backups)
                    if file_time.tzinfo is None:
                        file_time = file_time.replace(tzinfo=UTC)
                except (ValueError, TypeError):
                    # Invalid timestamp format - use file mtime instead
                    pass

            backups.append(
                {
                    "backup_path": backup_file,
                    "metadata_path": json_file if json_file.exists() else None,
                    "file_size": file_size,
                    "backup_timestamp": file_time,
                    "migration_version": metadata.get("migration_version"),
                    "application_version": metadata.get("application_version"),
                    "projects": metadata.get("projects", []),
                }
            )

        # Sort by timestamp (newest first)
        backups.sort(key=lambda b: b["backup_timestamp"], reverse=True)
        return backups

    def restore_backup(self, backup_path: Path) -> dict[str, Any] | None:
        """
        Restore a backup file over the current database.

        Args:
            backup_path: Path to the backup file to restore

        Returns:
            Dictionary containing backup metadata, or None if restore failed

        """
        if not backup_path.exists():
            return None

        # Create a backup of current database before restoring
        _ = self.create_backup()

        # Copy backup file over current database
        try:
            shutil.copy2(backup_path, self.db_path)
        except (OSError, PermissionError) as e:
            print(f"Failed to restore backup file: {e}")  # noqa: T201
            return None

        # Load metadata from JSON file
        json_file = backup_path.with_suffix(".json")
        metadata: dict[str, Any] = {}
        if json_file.exists():
            try:
                with json_file.open("r", encoding="utf-8") as f:
                    metadata = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                print(f"Failed to load backup metadata: {e}")  # noqa: T201
                # Continue - restore was successful even if metadata is missing

        return metadata
