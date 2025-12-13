"""Unit tests for database setup."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from oeapp.db import (
    Base,
    SessionLocal,
    create_engine_with_path,
    get_project_db_path,
    table_to_model_name,
)


class TestBase:
    """Test cases for Base declarative base."""

    def test_base_has_metadata(self):
        """Test Base has metadata attribute."""
        assert hasattr(Base, "metadata")
        assert Base.metadata is not None

    def test_base_has_registry(self):
        """Test Base has registry for models."""
        assert hasattr(Base, "registry")


class TestGetProjectDbPath:
    """Test cases for get_project_db_path()."""

    def test_returns_path_on_darwin(self, monkeypatch):
        """Test returns correct path on macOS."""
        monkeypatch.setattr(sys, "platform", "darwin")
        db_path = get_project_db_path()
        assert isinstance(db_path, Path)
        assert "Library" in str(db_path)
        assert "Application Support" in str(db_path)
        assert "Ænglisc Toolkit" in str(db_path)
        assert db_path.name == "default.db"

    def test_returns_path_on_linux(self, monkeypatch):
        """Test returns correct path on Linux."""
        monkeypatch.setattr(sys, "platform", "linux")
        db_path = get_project_db_path()
        assert isinstance(db_path, Path)
        assert ".config" in str(db_path)
        assert "Ænglisc Toolkit" in str(db_path)
        assert db_path.name == "default.db"

    def test_returns_path_on_windows(self, monkeypatch):
        """Test returns correct path on Windows."""
        monkeypatch.setattr(sys, "platform", "win32")
        db_path = get_project_db_path()
        assert isinstance(db_path, Path)
        assert "AppData" in str(db_path)
        assert "Local" in str(db_path)
        assert "Ænglisc Toolkit" in str(db_path)
        assert db_path.name == "default.db"

    def test_raises_value_error_for_unsupported_platform(self, monkeypatch):
        """Test raises ValueError for unsupported platform."""
        monkeypatch.setattr(sys, "platform", "unsupported")
        with pytest.raises(ValueError, match="Unsupported platform"):
            get_project_db_path()

    def test_creates_directory_if_not_exists(self, monkeypatch, tmp_path):
        """Test creates directory if it doesn't exist."""
        monkeypatch.setattr(sys, "platform", "darwin")
        # Mock Path.home() to return tmp_path
        with patch("pathlib.Path.home", return_value=tmp_path):
            db_path = get_project_db_path()
            assert db_path.parent.exists()


class TestCreateEngineWithPath:
    """Test cases for create_engine_with_path()."""

    def test_creates_engine_with_default_path(self):
        """Test creates engine with default path when None provided."""
        engine = create_engine_with_path(None)
        assert engine is not None
        assert engine.url.database is not None

    def test_creates_engine_with_custom_path(self, tmp_path):
        """Test creates engine with custom path."""
        db_path = tmp_path / "test.db"
        engine = create_engine_with_path(db_path)
        assert engine is not None
        assert db_path.exists()

    def test_creates_database_file_if_not_exists(self, tmp_path):
        """Test creates database file if it doesn't exist."""
        db_path = tmp_path / "new.db"
        assert not db_path.exists()
        create_engine_with_path(db_path)
        assert db_path.exists()


class TestSessionLocal:
    """Test cases for SessionLocal."""

    def test_session_local_is_defined(self):
        """Test SessionLocal is defined."""
        assert SessionLocal is not None
        assert callable(SessionLocal)

    def test_session_local_creates_session(self):
        """Test SessionLocal creates a session."""
        session = SessionLocal()
        assert session is not None
        session.close()


class TestTableToModelName:
    """Test cases for table_to_model_name()."""

    def test_converts_plural_table_name(self):
        """Test converts plural table name to singular model name."""
        result = table_to_model_name("projects")
        assert result == "Project"

    def test_converts_singular_table_name(self):
        """Test converts singular table name (no 's' ending)."""
        result = table_to_model_name("project")
        assert result == "Project"

    def test_handles_empty_string(self):
        """Test handles empty string."""
        result = table_to_model_name("")
        assert result == ""

    def test_handles_single_character(self):
        """Test handles single character."""
        result = table_to_model_name("s")
        assert result == ""

