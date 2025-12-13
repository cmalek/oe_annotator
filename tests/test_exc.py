"""Unit tests for custom exceptions."""

from pathlib import Path

import pytest

from oeapp.exc import (
    AlreadyExists,
    BackupFailed,
    DoesNotExist,
    MigrationCreationFailed,
    MigrationFailed,
    MigrationSkipped,
)


class TestDoesNotExist:
    """Test cases for DoesNotExist exception."""

    def test_creates_exception_with_resource_type_and_id(self):
        """Test creates exception with resource type and ID."""
        exc = DoesNotExist("Project", 123)
        assert exc.resource_type == "Project"
        assert exc.resource_id == 123
        assert "Project" in str(exc)
        assert "123" in str(exc)

    def test_creates_exception_with_string_id(self):
        """Test creates exception with string ID."""
        exc = DoesNotExist("Project", "test-name")
        assert exc.resource_type == "Project"
        assert exc.resource_id == "test-name"
        assert "test-name" in str(exc)

    def test_inherits_from_exception(self):
        """Test exception inherits from Exception."""
        exc = DoesNotExist("Project", 123)
        assert isinstance(exc, Exception)


class TestAlreadyExists:
    """Test cases for AlreadyExists exception."""

    def test_creates_exception_with_resource_type_and_id(self):
        """Test creates exception with resource type and ID."""
        exc = AlreadyExists("Project", "test-project")
        assert exc.resource_type == "Project"
        assert exc.resource_id == "test-project"
        assert "Project" in str(exc)
        assert "test-project" in str(exc)

    def test_creates_exception_with_integer_id(self):
        """Test creates exception with integer ID."""
        exc = AlreadyExists("Project", 123)
        assert exc.resource_type == "Project"
        assert exc.resource_id == 123
        assert "123" in str(exc)

    def test_inherits_from_exception(self):
        """Test exception inherits from Exception."""
        exc = AlreadyExists("Project", "test")
        assert isinstance(exc, Exception)


class TestMigrationCreationFailed:
    """Test cases for MigrationCreationFailed exception."""

    def test_creates_exception_with_error(self):
        """Test creates exception with error."""
        error = ValueError("Test error")
        exc = MigrationCreationFailed(error)
        assert exc.error == error
        assert "Migration creation failed" in str(exc)
        assert "Test error" in str(exc)

    def test_inherits_from_exception(self):
        """Test exception inherits from Exception."""
        error = ValueError("Test")
        exc = MigrationCreationFailed(error)
        assert isinstance(exc, Exception)


class TestMigrationFailed:
    """Test cases for MigrationFailed exception."""

    def test_creates_exception_with_all_attributes(self):
        """Test creates exception with all attributes."""
        error = ValueError("Migration error")
        exc = MigrationFailed(
            error=error,
            backup_app_version="1.0.0",
            backup_migration_version="abc123",
        )
        assert exc.error == error
        assert exc.backup_app_version == "1.0.0"
        assert exc.backup_migration_version == "abc123"
        assert "Migration failed" in str(exc)
        assert "Migration error" in str(exc)

    def test_creates_exception_with_none_versions(self):
        """Test creates exception with None versions."""
        error = ValueError("Migration error")
        exc = MigrationFailed(
            error=error,
            backup_app_version=None,
            backup_migration_version=None,
        )
        assert exc.error == error
        assert exc.backup_app_version is None
        assert exc.backup_migration_version is None

    def test_inherits_from_exception(self):
        """Test exception inherits from Exception."""
        error = ValueError("Test")
        exc = MigrationFailed(error, None, None)
        assert isinstance(exc, Exception)


class TestMigrationSkipped:
    """Test cases for MigrationSkipped exception."""

    def test_creates_exception_with_skip_version(self):
        """Test creates exception with skip version."""
        exc = MigrationSkipped("1.0.0")
        assert exc.skip_until_version == "1.0.0"
        assert "Migration skipped" in str(exc)
        assert "1.0.0" in str(exc)

    def test_inherits_from_exception(self):
        """Test exception inherits from Exception."""
        exc = MigrationSkipped("1.0.0")
        assert isinstance(exc, Exception)


class TestBackupFailed:
    """Test cases for BackupFailed exception."""

    def test_creates_exception_with_error_and_path(self):
        """Test creates exception with error and backup path."""
        error = IOError("Permission denied")
        backup_path = Path("/tmp/backup.db")
        exc = BackupFailed(error, backup_path)
        assert exc.error == error
        assert exc.backup_path == backup_path
        assert "Backup failed" in str(exc)
        assert "Permission denied" in str(exc)

    def test_inherits_from_exception(self):
        """Test exception inherits from Exception."""
        error = IOError("Test")
        backup_path = Path("/tmp/backup.db")
        exc = BackupFailed(error, backup_path)
        assert isinstance(exc, Exception)

