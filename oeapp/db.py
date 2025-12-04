"""SQLAlchemy database setup for Ænglisc Toolkit."""

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, cast

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

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
        ``AppData/Local/Ænglisc Toolkit/projects`` directory.
    - On macOS, the database is created in the user's
        ``~/Library/Application Support/Ænglisc Toolkit/projects`` directory.
    - On Linux, the database is created in the user's
        ``~/.config/Ænglisc Toolkit/projects`` directory.
    - If the platform is not supported, raise a ValueError.

    Returns:
        Path to the database file

    """
    if sys.platform not in ["win32", "darwin", "linux"]:
        msg = f"Unsupported platform: {sys.platform}"
        raise ValueError(msg)
    if sys.platform == "win32":
        db_path = Path.home() / "AppData" / "Local" / "Ænglisc Toolkit" / "projects"
    elif sys.platform == "darwin":
        db_path = (
            Path.home()
            / "Library"
            / "Application Support"
            / "Ænglisc Toolkit"
            / "projects"
        )
    elif sys.platform == "linux":
        db_path = Path.home() / ".config" / "Ænglisc Toolkit" / "projects"
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


def table_to_model_name(table_name: str) -> str:
    """
    Convert table name to model name.

    Args:
        table_name: Database table name

    Returns:
        Model name

    """
    # Simple mapping: plural table names to singular model names
    # This is a basic implementation - may need refinement
    if table_name.endswith("s"):
        return table_name[:-1].capitalize()
    return table_name.capitalize()
