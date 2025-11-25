"""Service for handling database migrations."""

import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, cast

from alembic import command
from alembic.config import Config
from alembic.script import Script, ScriptDirectory
from PySide6.QtCore import QSettings
from sqlalchemy import inspect, text

from oeapp import __version__
from oeapp.db import (
    Base,
    create_engine_with_path,
    table_to_model_name,
)
from oeapp.exc import (
    BackupFailed,
    MigrationCreationFailed,
    MigrationFailed,
    MigrationSkipped,
)

from .backup import BackupService
from .mixins import ProjectFoldersMixin


@dataclass
class MigrationResult:
    """Result of a migration."""

    # The application version
    app_version: str | None
    # The curren database migration version
    migration_version: str


@dataclass
class MigrationCreationResult:
    """Service for handling migration files."""

    # The migration file path
    migration_file_path: Path
    # The revision ID
    revision_id: str


class MigrationMetadataService(ProjectFoldersMixin):
    """
    Service for handling migration metadata.

    This handles two files:

    - migration_versions.json: This file contains the migration versions and the
      minimum app version required for each migration.

    """

    @property
    def versions(self) -> dict[str, Any] | None:
        """
        Read migration versions metadata from JSON file.

        Returns:
            Migration versions metadata dictionary, or None if not found

        """
        if not self.MIGRATION_VERSIONS_PATH.exists():
            return None
        try:
            with self.MIGRATION_VERSIONS_PATH.open("r", encoding="utf-8") as f:
                metadata = json.load(f)
        except (OSError, PermissionError, json.JSONDecodeError):
            return None
        return metadata

    @versions.setter
    def versions(self, metadata: dict[str, Any]) -> None:
        """
        Write migration versions metadata to JSON file.

        Args:
            metadata: Migration versions metadata dictionary

        """
        self.MIGRATION_VERSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with self.MIGRATION_VERSIONS_PATH.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
            f.write("\n")

    def get_min_version_for_migration(self, migration_version: str) -> str | None:
        """
        Get the minimum app version required for a given migration version.

        Args:
            migration_version: Migration revision ID

        Returns:
            Minimum app version string, or None if not found

        """
        if self.versions is None:
            return None
        try:
            return self.versions.get(migration_version)
        except KeyError:
            return None

    def update(self, revision: str, min_version: str) -> None:
        """
        Update migration_versions.json with new migration.

        Ensures only one migration SHA per version (the latest one).

        Args:
            revision: Migration revision ID
            min_version: Minimum app version required

        """
        migration_metadata_service = MigrationMetadataService()
        versions = migration_metadata_service.versions
        if versions is None:
            versions = {}
        # Remove any existing migration SHA that maps to this version
        # (to ensure only the latest migration SHA per version)
        keys_to_remove = [
            old_revision
            for old_revision, old_version in versions.items()
            if old_version == min_version
        ]
        for key in keys_to_remove:
            del versions[key]

        # Add the new migration SHA for this version
        versions[revision] = min_version
        migration_metadata_service.versions = versions
        if keys_to_remove:
            print(  # noqa: T201
                f"Updated {migration_metadata_service.MIGRATION_VERSIONS_PATH!s}: "
                f"Replaced {keys_to_remove} with {revision} for version "
                f"{min_version}"
            )
        else:
            print(  # noqa: T201
                f"Updated {migration_metadata_service.MIGRATION_VERSIONS_PATH!s} with "
                f"{revision}: {min_version}"
            )


class FieldMappingService(ProjectFoldersMixin):
    """Service for handling field mappings."""

    ALTER_COLUMN_PATTERN: Final[re.Pattern[str]] = re.compile(
        r'batch_op\.alter_column\(["\']([^"\']+)["\'][^)]*new_column_name\s*=\s*["\']([^"\']+)["\']'
    )
    ALTER_TABLE_PATTERN: Final[re.Pattern[str]] = re.compile(
        r'batch_alter_table\(["\']([^"\']+)["\']'
    )

    @property
    def mapping(self) -> dict[str, Any]:
        """
        Read field mappings from JSON file.

        Returns:
            Field mappings dictionary, or None if not found

        """
        if not self.FIELD_MAPPINGS_PATH.exists():
            return {}
        try:
            with self.FIELD_MAPPINGS_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, PermissionError, json.JSONDecodeError):
            return {}

    @mapping.setter
    def mapping(self, mappings: dict[str, Any]) -> None:
        """
        Write field mappings to JSON file.
        """
        self.FIELD_MAPPINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with self.FIELD_MAPPINGS_PATH.open("w", encoding="utf-8") as f:
            json.dump(mappings, f, indent=2)
        f.write("\n")

    def update(self, migration_file: Path) -> bool:
        """
        Update field mappings with new migration, but only if renames are provided.

        Args:
            migration_file: Path to the migration file

        Returns:
            True if the field mappings were updated, False otherwise

        """
        revision_id, renames = self.discover(migration_file)
        mappings = self.mapping
        if renames:
            mappings[revision_id] = renames
            self.mapping = mappings
            return True
        return False

    def discover(self, migration_file: Path) -> tuple[str, dict[str, dict[str, str]]]:
        """
        Discover field renames from a migration file.

        Args:
            migration_file: Path to the migration file

        Returns:
            Tuple containing the revision ID and the field renames

        """
        renames: dict[str, dict[str, str]] = {}

        # Read file content
        with Path(migration_file).open("r", encoding="utf-8") as f:
            content = f.read()

        migration_service = MigrationService()
        revision_id = migration_service.extract_revision_id(migration_file)

        # Look for batch_op.alter_column() calls with new_column_name parameter
        # Pattern: batch_op.alter_column("old_name", new_column_name="new_name", ...)
        matches = self.ALTER_COLUMN_PATTERN.finditer(content)
        for match in matches:
            old_name = match.group(1)
            new_name = match.group(2)

            # Try to determine table/model name from context
            # Look backwards for table name in batch_alter_table
            before_match = content[: match.start()]
            table_match = self.ALTER_TABLE_PATTERN.search(before_match)
            if table_match:
                table_name = table_match.group(1)
                model_name = table_to_model_name(table_name)
                if model_name not in renames:
                    renames[table_name] = {}
                renames[table_name][old_name] = new_name
        return revision_id, renames


class BackupFileMetadataService:
    """
    Service for handling backup file metadata.

    This handles the metadata JSON file for each backup file.

    Args:
        backup_path: Path to the backup file

    Raises:
        FileNotFoundError: If the backup file metadata JSON file is not found

    """

    def __init__(self, backup_path: Path) -> None:
        """Initialize backup file metadata service."""
        json_file = backup_path.with_suffix(".json")
        if not json_file.exists():
            msg = f"Backup file metadata JSON file not found: {json_file}"
            raise FileNotFoundError(msg)
        self.backup_path = json_file

    @property
    def metadata(self) -> dict[str, Any]:
        """
        Read metadata from backup file metadata JSON file.

        Args:
            backup_path: Path to the backup file

        Returns:
            Metadata dictionary, or None if not found

        """
        try:
            with self.backup_path.open("r", encoding="utf-8") as f:
                metadata = json.load(f)
        except FileNotFoundError:
            return {}
        return metadata

    @property
    def migration_version(self) -> str | None:
        """
        Read migration version from backup metadata JSON.

        Args:
            backup_path: Path to the backup file

        Returns:
            Migration version string, or None if not found

        """
        return self.metadata.get("migration_version")

    @property
    def app_version(self) -> str | None:
        """
        Read application version from backup metadata JSON.

        Returns:
            Application version string, or None if not found

        """
        return self.metadata.get("application_version")


class MigrationService(ProjectFoldersMixin):
    """Service for handling database migrations."""

    #: Regex for extracting the revision ID from a migration file
    REVISION_ID_REGEX: Final[re.Pattern[str]] = re.compile(
        r'revision\s*:\s*str\s*=\s*["\']([^"\']+)["\']'
    )

    def __init__(self) -> None:
        """
        Initialize migration service.

        Args:
            session: SQLAlchemy session

        """
        self.backup_service = BackupService()
        self.engine = create_engine_with_path()
        self.migration_metadata_service = MigrationMetadataService()

    @property
    def config(self) -> Config:
        """
        Get the Alembic configuration.

        Returns:
            Alembic configuration

        """
        return Config(str(self.ALEMBIC_INI_PATH))

    @property
    def script(self) -> ScriptDirectory:
        """
        Get the Alembic script.

        Returns:
            Alembic script

        """
        return ScriptDirectory.from_config(self.config)

    def last_working_migration_version(self) -> str | None:
        """
        Get the last known working migration version from QSettings.

        Returns:
            Migration version string, or None if not set

        """
        settings = QSettings()
        return cast(
            "str | None",
            settings.value("migration/last_working_version", None, type=str),
        )

    def newest_migration_file(self) -> Path | None:
        """
        Get the newest migration file from the migrations directory.

        Returns:
            Path to the newest migration file, or None if no migrations exist

        """
        migration_files = sorted(
            self.MIGRATIONS_DIR.glob("*.py"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return migration_files[0] if migration_files else None

    def file_migration_version(self, migration_file: Path) -> str | None:
        """
        Get the migration version from a migration file.
        """
        return self.extract_revision_id(migration_file)

    def latest_migration_version(self) -> str | None:
        """
        Get the latest migration version from Alembic.
        """
        filename = self.newest_migration_file()
        if filename is None:
            return None
        return self.extract_revision_id(filename)

    def db_migration_version(self) -> str | None:
        """
        Get the current database migration version from Alembic.

        Returns:
            Migration version string, or None if no version is set

        """
        db_inspector = inspect(self.engine)
        existing_tables = db_inspector.get_table_names()

        if "alembic_version" not in existing_tables:
            return None

        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            )
            row = result.fetchone()
            if row:
                return row[0]
        return None

    def code_migration_version(self) -> str | None:
        """
        Get the head migration version from Alembic (what code expects).

        Returns:
            Head migration version string, or None if no migrations exist

        """
        return self.script.get_current_head()

    def revision_chain(self, from_version: str, to_version: str) -> list[str]:  # noqa: PLR0912
        """
        Get ordered list of migration revision IDs from one version to another.

        Args:
            from_version: Starting migration version (export version)
            to_version: Target migration version (current version)

        Returns:
            Ordered list of migration revision IDs (from oldest to newest)

        """
        # Build a map of down_revision -> list of revisions that have it
        # This allows us to walk forward from from_version to to_version
        forward_map: dict[str | None, list[str]] = {}
        revision_to_down: dict[str, str | None] = {}

        for script_revision in self.script.walk_revisions():
            rev_id = script_revision.revision
            down_rev = script_revision.down_revision
            if isinstance(down_rev, str):
                revision_to_down[rev_id] = down_rev
                if down_rev not in forward_map:
                    forward_map[down_rev] = []
                forward_map[down_rev].append(rev_id)
            elif isinstance(down_rev, (list, tuple)) and down_rev:
                # Handle multiple down revisions - take first one
                revision_to_down[rev_id] = down_rev[0]
                if down_rev[0] not in forward_map:
                    forward_map[down_rev[0]] = []
                forward_map[down_rev[0]].append(rev_id)
            else:
                revision_to_down[rev_id] = None
                if None not in forward_map:
                    forward_map[None] = []
                forward_map[None].append(rev_id)

        # If versions are the same, return empty list
        if from_version == to_version:
            return []

        # Walk forward from from_version to to_version
        chain: list[str] = []
        current = from_version
        visited: set[str] = set()

        while current and current != to_version:
            if current in visited:
                # Circular reference or invalid chain
                break
            visited.add(current)

            # Find next revision(s) that have current as down_revision
            if current in forward_map:
                next_revisions = forward_map[current]
                if next_revisions:
                    # Take the first one (assuming linear chain)
                    # If there are multiple, we might need more sophisticated logic
                    current = next_revisions[0]
                    chain.append(current)
                else:
                    break
            else:
                break

        return chain

    def should_abort(self, skip_until_version: str | None = None) -> bool:
        """
        The user can put in their settings the maximum version they want to
        migrate to.  If the current database version is greater than the version
        the user wants to migrate to, the migrations will be aborted.

        Args:
            skip_until_version (_type_, optional): _description_. Defaults to None.

        Returns:
            True if the migrations should be aborted, False otherwise

        """
        current_db_version = self.db_migration_version()
        # Compare versions as strings (Alembic versions are hex strings)
        return bool(
            current_db_version and str(current_db_version) < str(skip_until_version)
        )

    def restore(self, backup_path: Path) -> tuple[str | None, str | None]:
        """
        Restore the database from a backup after a failed migration

        Args:
            backup_path: Path to the backup file to restore

        Returns:
            Tuple containing the backup application version and the backup
            migration version, or None if the backup failed

        """
        metadata = self.backup_service.restore_backup(backup_path)
        backup_app_version = None
        if metadata:
            backup_app_version = metadata.get("application_version")
            migration_version = metadata.get("migration_version")
            return backup_app_version, migration_version
        return None, None

    def create(self, name: str) -> MigrationCreationResult:
        """
        Create a new migration.

        Args:
            name: Migration name

        Returns:
            Migration revision ID

        """
        result = command.revision(self.config, message=name, autogenerate=True)
        if result is None:
            msg = f"Failed to create migration: {name}"
            raise MigrationCreationFailed(Exception(msg))
        result = cast("Script", result)
        self.migration_metadata_service.update(result.revision, __version__)
        return MigrationCreationResult(
            migration_file_path=Path(result.path),
            revision_id=result.revision,
        )

    def migrate(self, skip_until_version: str | None = None) -> MigrationResult:
        """
        Migrate the database to the latest version.

        Args:
            skip_until_version: Version to skip migrations up to

        Raises:
            MigrationFailed: If the migration fails
            MigrationSkipped: If the migration is skipped

        """
        if skip_until_version:
            if self.should_abort(skip_until_version):
                raise MigrationSkipped(skip_until_version)

        try:
            backup_path = self.backup_service.create_backup()
        except BackupFailed as e:
            raise MigrationFailed(e, None, None) from e
        try:
            migration_result = self.apply_migrations()
        except Exception as e:
            # Migration failed - restore backup if we have one
            app_version, migration_version = self.restore(backup_path)
            raise MigrationFailed(e, app_version, migration_version) from e

        return migration_result

    def apply_migrations(self) -> MigrationResult:
        """
        Apply pending Alembic migrations.

        This should be called on application startup.
        Raises an exception if migrations fail.

        Raises:
            Exception: If migration fails

        Returns:
            Tuple containing the current database migration version and the
            current application version

        """
        # Check if database is fresh (no alembic_version table)
        db_inspector = inspect(self.engine)
        existing_tables = db_inspector.get_table_names()

        if "alembic_version" not in existing_tables:
            # Fresh database - create tables from models
            Base.metadata.create_all(self.engine)
            # Create alembic_version table and mark initial migration as applied
            initial_version = self.latest_migration_version()
            with self.engine.connect() as conn:
                conn.execute(
                    text(
                        "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, PRIMARY KEY (version_num))"  # noqa: E501
                    )
                )
                conn.execute(
                    text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
                    {"version": initial_version},
                )
                conn.commit()
            return MigrationResult(
                app_version=__version__,
                migration_version=cast("str", initial_version),
            )
        # Existing database - apply migrations normally
        command.upgrade(self.config, "head")
        # Migration succeeded - return current version
        current_version = self.db_migration_version()
        return MigrationResult(
            app_version=__version__,
            migration_version=cast("str", current_version),
        )

    def extract_revision_id(self, migration_file: Path) -> str:
        """
        Extract the revision ID from a migration file.

        Args:
            migration_file: Path to the migration file

        Returns:
            Revision ID, or None if not found

        Raises:
            FileNotFoundError: If the migration file is not found
            SyntaxError: If the migration file is not a valid Python file
            OSError: If the migration file cannot be read
            PermissionError: If the migration file cannot be read
            KeyError: If the revision ID is not found

        """
        # Read file content
        with Path(migration_file).open("r", encoding="utf-8") as f:
            content = f.read()

        # Look for revision = "..." pattern
        match = self.REVISION_ID_REGEX.search(content)
        if match:
            return cast("str", match.group(1))

        # Try parsing as Python AST
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "revision":
                        if isinstance(node.value, ast.Constant):
                            return node.value.value
                        if sys.version_info < (3, 8) and isinstance(
                            node.value, ast.Str
                        ):  # Python < 3.8
                            return node.value.s

        msg = f"Revision ID not found in migration file: {migration_file}"
        raise KeyError(msg)
