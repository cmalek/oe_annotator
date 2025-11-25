"""Utility functions for Ænglisc Toolkit."""

import sys
from datetime import UTC, datetime
from pathlib import Path


def get_resource_path(relative_path: str) -> Path:
    """
    Get resource path for bundled application or development.

    Args:
        relative_path: Relative path from project root

    Returns:
        Path to resource file

    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running in PyInstaller bundle
        base_path = Path(sys._MEIPASS)
    else:
        # Running in development
        base_path = Path(__file__).parent.parent
    return base_path / relative_path


def to_utc_iso(dt: datetime | None) -> str | None:
    """
    Convert datetime to UTC ISO format string.

    Args:
        dt: Datetime object to convert, or None

    Returns:
        ISO format string with UTC timezone, or None

    """
    if dt is None:
        return None
    # If datetime is naive, assume it's already UTC (database stores UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    # Convert to UTC if not already
    dt_utc = dt.astimezone(UTC)
    return dt_utc.isoformat()


def from_utc_iso(iso_str: str | None) -> datetime | None:
    """
    Parse UTC ISO format string to datetime.

    Args:
        iso_str: ISO format string, or None

    Returns:
        Naive datetime object (UTC), or None

    """
    if iso_str is None:
        return None
    dt = datetime.fromisoformat(iso_str)
    # Ensure it's in UTC
    dt = dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)
    # Return naive datetime (SQLite doesn't handle timezone-aware datetimes well)
    return dt.replace(tzinfo=None)
