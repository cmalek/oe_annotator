"""SQLAlchemy database setup for Old English Annotator."""

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, cast

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from PySide6.QtCore import QSettings
from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from oeapp import __version__

if TYPE_CHECKING:
    import sqlite3

#: The default database name.
DEFAULT_DB_NAME: Final[str] = "default.db"


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


def get_project_db_path() -> Path:
    """
    Get the path to the project database.

    - On Windows, the database is created in the user's
        ``AppData/Local/oe_annotator/projects`` directory.
    - On macOS, the database is created in the user's
        ``~/Library/Application Support/oe_annotator/projects`` directory.
    - On Linux, the database is created in the user's
        ``~/.config/oe_annotator/projects`` directory.
    - If the platform is not supported, raise a ValueError.

    Returns:
        Path to the database file

    """
    if sys.platform not in ["win32", "darwin", "linux"]:
        msg = f"Unsupported platform: {sys.platform}"
        raise ValueError(msg)
    if sys.platform == "win32":
        db_path = Path.home() / "AppData" / "Local" / "oe_annotator" / "projects"
    elif sys.platform == "darwin":
        db_path = (
            Path.home()
            / "Library"
            / "Application Support"
            / "oe_annotator"
            / "projects"
        )
    elif sys.platform == "linux":
        db_path = Path.home() / ".config" / "oe_annotator" / "projects"
    db_path.mkdir(parents=True, exist_ok=True)
    return db_path / DEFAULT_DB_NAME


def create_engine_with_path(db_path: Path | None = None) -> Engine:
    """
    Create SQLAlchemy engine with proper SQLite settings.

    Args:
        db_path: Optional path to database file. If None, uses default path.

    Returns:
        SQLAlchemy engine

    """
    if db_path is None:
        db_path = get_project_db_path()

    # Create the file if it doesn't exist
    db_path.touch(exist_ok=True)

    # Create engine with SQLite-specific settings
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},  # Allow multi-threaded access
        echo=False,  # Set to True for SQL debugging
    )

    # Enable foreign keys and WAL mode
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(
        dbapi_conn: sqlite3.Connection | Any, _connection_record: Any
    ) -> None:
        """Set SQLite pragmas on connection."""
        cursor = cast("sqlite3.Cursor", dbapi_conn.cursor())
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    return engine


# Create default engine and session factory
_engine = create_engine_with_path()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_session():
    """
    Get a database session.

    Yields:
        SQLAlchemy session

    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_current_db_migration_version() -> str | None:
    """
    Get the current database migration version from Alembic.

    Returns:
        Migration version string, or None if no version is set

    """
    db_inspector = inspect(_engine)
    existing_tables = db_inspector.get_table_names()

    if "alembic_version" not in existing_tables:
        return None

    with _engine.connect() as conn:
        result = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        row = result.fetchone()
        if row:
            return row[0]
    return None


def get_current_code_migration_version() -> str | None:
    """
    Get the head migration version from Alembic (what code expects).

    Returns:
        Head migration version string, or None if no migrations exist

    """
    alembic_ini_path = Path(__file__).parent / "etc" / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    script = ScriptDirectory.from_config(alembic_cfg)
    return script.get_current_head()


def get_last_working_migration_version() -> str | None:
    """
    Get the last known working migration version from QSettings.

    Returns:
        Migration version string, or None if not set

    """
    settings = QSettings()
    return cast(
        "str | None", settings.value("migration/last_working_version", None, type=str)
    )


def get_backup_migration_version(backup_path: Path) -> str | None:
    """
    Read migration version from backup metadata JSON.

    Args:
        backup_path: Path to the backup file

    Returns:
        Migration version string, or None if not found

    """
    json_file = backup_path.with_suffix(".json")
    if not json_file.exists():
        return None

    # Read and parse JSON file - can fail with file or JSON errors
    try:
        with json_file.open("r", encoding="utf-8") as f:
            metadata = json.load(f)
    except (OSError, PermissionError, json.JSONDecodeError):
        return None

    # Extract migration version - metadata.get() is safe even if not a dict
    if isinstance(metadata, dict):
        return metadata.get("migration_version")
    return None


def get_backup_app_version(backup_path: Path) -> str | None:
    """
    Read application version from backup metadata JSON.

    Args:
        backup_path: Path to the backup file

    Returns:
        Application version string, or None if not found

    """
    json_file = backup_path.with_suffix(".json")
    if not json_file.exists():
        return None

    # Read and parse JSON file - can fail with file or JSON errors
    try:
        with json_file.open("r", encoding="utf-8") as f:
            metadata = json.load(f)
    except (OSError, PermissionError, json.JSONDecodeError):
        return None

    # Extract application version - metadata.get() is safe even if not a dict
    if isinstance(metadata, dict):
        return metadata.get("application_version")
    return None


def get_min_version_for_migration(migration_version: str) -> str | None:
    """
    Get the minimum app version required for a given migration version.

    Args:
        migration_version: Migration revision ID

    Returns:
        Minimum app version string, or None if not found

    """
    migration_versions_path = Path(__file__).parent / "etc" / "migration_versions.json"
    if not migration_versions_path.exists():
        return None

    try:
        with migration_versions_path.open("r", encoding="utf-8") as f:
            migration_versions = json.load(f)
    except (OSError, PermissionError, json.JSONDecodeError):
        return None

    if isinstance(migration_versions, dict):
        return migration_versions.get(migration_version)
    return None


def apply_migrations() -> None:
    """
    Apply pending Alembic migrations.

    This should be called on application startup.
    Raises an exception if migrations fail.

    Raises:
        Exception: If migration fails

    """
    settings = QSettings()

    # Check if database is fresh (no alembic_version table)
    db_inspector = inspect(_engine)
    existing_tables = db_inspector.get_table_names()

    if "alembic_version" not in existing_tables:
        # Fresh database - create tables from models
        Base.metadata.create_all(_engine)
        # Create alembic_version table and mark initial migration as applied
        initial_version = "57399ca978ee"
        with _engine.connect() as conn:
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
        # Store successful migration version
        settings.setValue("migration/last_working_version", initial_version)
        settings.setValue("app/current_version", __version__)
    else:
        # Existing database - apply migrations normally
        alembic_ini_path = Path(__file__).parent / "etc" / "alembic.ini"
        alembic_cfg = Config(str(alembic_ini_path))
        command.upgrade(alembic_cfg, "head")
        # Migration succeeded - store current version
        current_version = get_current_db_migration_version()
        if current_version:
            settings.setValue("migration/last_working_version", current_version)
        settings.setValue("app/current_version", __version__)
