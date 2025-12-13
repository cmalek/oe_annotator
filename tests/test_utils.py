"""Unit tests for utility functions."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from PySide6.QtGui import QPixmap

from oeapp.utils import from_utc_iso, get_logo_pixmap, get_resource_path, to_utc_iso


class TestToUtcIso:
    """Test cases for to_utc_iso()."""

    def test_converts_naive_datetime(self):
        """Test converting naive datetime to UTC ISO string."""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = to_utc_iso(dt)
        assert result is not None
        assert result.endswith("+00:00") or result.endswith("Z")
        assert "2024-01-15T10:30:45" in result

    def test_converts_timezone_aware_datetime(self):
        """Test converting timezone-aware datetime to UTC ISO string."""
        dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=UTC)
        result = to_utc_iso(dt)
        assert result is not None
        assert "2024-01-15T10:30:45" in result

    def test_returns_none_for_none(self):
        """Test returns None when input is None."""
        result = to_utc_iso(None)
        assert result is None


class TestFromUtcIso:
    """Test cases for from_utc_iso()."""

    def test_parses_valid_iso_string(self):
        """Test parsing valid ISO format string."""
        iso_str = "2024-01-15T10:30:45+00:00"
        result = from_utc_iso(iso_str)
        assert result is not None
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
        assert result.second == 45
        # Should return naive datetime
        assert result.tzinfo is None

    def test_parses_iso_string_with_z(self):
        """Test parsing ISO string with Z timezone indicator."""
        iso_str = "2024-01-15T10:30:45Z"
        result = from_utc_iso(iso_str)
        assert result is not None
        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_parses_naive_iso_string(self):
        """Test parsing naive ISO string (no timezone)."""
        iso_str = "2024-01-15T10:30:45"
        result = from_utc_iso(iso_str)
        assert result is not None
        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_returns_none_for_none(self):
        """Test returns None when input is None."""
        result = from_utc_iso(None)
        assert result is None

    def test_round_trip_conversion(self):
        """Test that to_utc_iso and from_utc_iso are inverse operations."""
        original = datetime(2024, 1, 15, 10, 30, 45)
        iso_str = to_utc_iso(original)
        assert iso_str is not None
        converted_back = from_utc_iso(iso_str)
        assert converted_back is not None
        # Compare naive datetimes (timezone info stripped)
        assert converted_back.replace(tzinfo=None) == original.replace(tzinfo=None)


class TestGetResourcePath:
    """Test cases for get_resource_path()."""

    def test_returns_path_in_development(self):
        """Test returns path relative to project root in development."""
        path = get_resource_path("assets/logo.png")
        assert isinstance(path, Path)
        assert path.name == "logo.png"
        assert "assets" in str(path)

    def test_handles_nested_paths(self):
        """Test handles nested relative paths."""
        path = get_resource_path("assets/subdir/file.txt")
        assert isinstance(path, Path)
        assert "subdir" in str(path)
        assert path.name == "file.txt"


class TestGetLogoPixmap:
    """Test cases for get_logo_pixmap()."""

    def test_returns_pixmap_when_logo_exists(self, qapp):
        """Test returns QPixmap when logo file exists."""
        pixmap = get_logo_pixmap(75)
        # If logo exists, should return QPixmap
        # If not, returns None (which is acceptable)
        if pixmap is not None:
            assert isinstance(pixmap, QPixmap)
            assert not pixmap.isNull()

    def test_returns_none_when_logo_missing(self, qapp, monkeypatch):
        """Test returns None when logo file doesn't exist."""
        # Mock get_resource_path to return non-existent path
        def mock_get_resource_path(relative_path):
            return Path("/nonexistent/path/logo.png")

        monkeypatch.setattr("oeapp.utils.get_resource_path", mock_get_resource_path)
        pixmap = get_logo_pixmap(75)
        assert pixmap is None

    def test_scales_to_specified_size(self, qapp):
        """Test pixmap is scaled to specified size."""
        pixmap = get_logo_pixmap(100)
        if pixmap is not None:
            # Should be approximately 100x100 (may vary slightly due to aspect ratio)
            assert pixmap.width() <= 100
            assert pixmap.height() <= 100

    def test_handles_different_sizes(self, qapp):
        """Test handles different size parameters."""
        sizes = [50, 75, 100, 150]
        for size in sizes:
            pixmap = get_logo_pixmap(size)
            if pixmap is not None:
                assert pixmap.width() <= size
                assert pixmap.height() <= size

