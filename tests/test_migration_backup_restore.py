"""Unit tests for migration backup and restore functionality."""

import logging
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from oeapp.db import Base, get_project_db_path
from oeapp.exc import BackupFailed, MigrationFailed
from oeapp.services.migration import MigrationService


@pytest.fixture
def temp_db_path(tmp_path):
    """Create a temporary database path for testing."""
    db_path = tmp_path / "test.db"
    return db_path


@pytest.fixture
def temp_db_engine(temp_db_path):
    """Create a temporary database engine and initialize it."""
    engine = create_engine(f"sqlite:///{temp_db_path}")
    Base.metadata.create_all(engine)

    # Create alembic_version table
    with engine.connect() as conn:
        conn.execute(
            text(
                "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL, PRIMARY KEY (version_num))"
            )
        )
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:version)"),
            {"version": "test_version"},
        )
        conn.commit()

    yield engine

    engine.dispose()
    if temp_db_path.exists():
        temp_db_path.unlink()


@pytest.fixture
def migration_service_with_temp_db(temp_db_path, monkeypatch):
    """Create a MigrationService with a temporary database."""
    # Mock get_project_db_path to return our temp path
    monkeypatch.setattr("oeapp.services.migration.get_project_db_path", lambda: temp_db_path)

    # Create a new engine with the temp path
    with patch("oeapp.services.migration.create_engine_with_path") as mock_create:
        engine = create_engine(f"sqlite:///{temp_db_path}")
        mock_create.return_value = engine

        service = MigrationService()
        service.engine = engine
        yield service


class TestHasPendingMigrations:
    """Test has_pending_migrations() method."""

    def test_has_pending_migrations_when_db_behind(self, migration_service_with_temp_db, monkeypatch):
        """Test that has_pending_migrations returns True when DB is behind."""
        service = migration_service_with_temp_db

        # Mock versions to return a mapping
        mock_versions = {"newer_version": "0.1.0"}
        service.migration_metadata_service.versions = mock_versions

        # Mock code_migration_version to return a newer version
        with patch.object(service, "code_migration_version", return_value="newer_version"):
            with patch.object(service, "db_migration_version", return_value="test_version"):
                assert service.has_pending_migrations() is True

    def test_no_pending_migrations_when_db_up_to_date(self, migration_service_with_temp_db, monkeypatch):
        """Test that has_pending_migrations returns False when DB is up to date."""
        service = migration_service_with_temp_db

        # Mock versions
        mock_versions = {"current_version": "0.1.0"}
        service.migration_metadata_service.versions = mock_versions

        # Mock both versions to be the same
        with patch.object(service, "code_migration_version", return_value="current_version"):
            with patch.object(service, "db_migration_version", return_value="current_version"):
                assert service.has_pending_migrations() is False

    def test_has_pending_migrations_fresh_database(self, migration_service_with_temp_db):
        """Test that has_pending_migrations returns True for fresh database with migrations."""
        service = migration_service_with_temp_db

        # Mock db_migration_version to return None (fresh DB)
        with patch.object(service, "db_migration_version", return_value=None):
            with patch.object(service, "code_migration_version", return_value="some_version"):
                assert service.has_pending_migrations() is True

    def test_no_pending_migrations_fresh_database_no_migrations(self, migration_service_with_temp_db):
        """Test that has_pending_migrations returns False for fresh DB with no migrations."""
        service = migration_service_with_temp_db

        # Mock db_migration_version to return None (fresh DB)
        with patch.object(service, "db_migration_version", return_value=None):
            with patch.object(service, "code_migration_version", return_value=None):
                assert service.has_pending_migrations() is False


class TestPreMigrationBackup:
    """Test pre-migration backup methods."""

    def test_create_pre_migration_backup(self, temp_db_engine, temp_db_path, migration_service_with_temp_db):
        """Test that pre-migration backup is created."""
        service = migration_service_with_temp_db

        # Ensure database exists and is valid
        assert temp_db_path.exists()
        original_size = temp_db_path.stat().st_size

        backup_path = service._create_pre_migration_backup()

        assert backup_path.exists()
        assert backup_path.name == "test.db.pre-migration"
        assert backup_path.stat().st_size == original_size

    def test_create_pre_migration_backup_fails_when_db_missing(self, temp_db_path, migration_service_with_temp_db):
        """Test that backup creation fails when database doesn't exist."""
        service = migration_service_with_temp_db

        # Ensure DB doesn't exist
        if temp_db_path.exists():
            temp_db_path.unlink()

        with pytest.raises(BackupFailed):
            service._create_pre_migration_backup()

    def test_restore_pre_migration_backup(self, temp_db_engine, temp_db_path, migration_service_with_temp_db):
        """Test that pre-migration backup can be restored."""
        service = migration_service_with_temp_db

        # Ensure database exists and is valid
        assert temp_db_path.exists()
        original_size = temp_db_path.stat().st_size

        # Create backup
        backup_path = service._create_pre_migration_backup()

        # Modify database by writing new content (this will corrupt it, but that's fine for the test)
        temp_db_path.write_bytes(b"modified database")
        modified_size = temp_db_path.stat().st_size

        # Restore backup
        service._restore_pre_migration_backup()

        # Verify database was restored (size should match original)
        assert temp_db_path.stat().st_size == original_size

    def test_restore_pre_migration_backup_fails_when_backup_missing(self, temp_db_path, migration_service_with_temp_db):
        """Test that restore fails when backup doesn't exist."""
        service = migration_service_with_temp_db

        backup_path = service._get_pre_migration_backup_path()
        if backup_path.exists():
            backup_path.unlink()

        with pytest.raises(BackupFailed):
            service._restore_pre_migration_backup()

    def test_delete_pre_migration_backup(self, temp_db_path, migration_service_with_temp_db):
        """Test that pre-migration backup is deleted."""
        service = migration_service_with_temp_db

        # Create backup
        temp_db_path.write_bytes(b"test")
        backup_path = service._create_pre_migration_backup()
        assert backup_path.exists()

        # Delete backup
        service._delete_pre_migration_backup()

        assert not backup_path.exists()

    def test_delete_pre_migration_backup_when_missing(self, migration_service_with_temp_db):
        """Test that delete doesn't fail when backup doesn't exist."""
        service = migration_service_with_temp_db

        # Should not raise an exception
        service._delete_pre_migration_backup()


class TestMigrationFlow:
    """Test the complete migration flow."""

    def test_migrate_skips_when_no_pending_migrations(self, migration_service_with_temp_db):
        """Test that migrate() returns early when no pending migrations."""
        service = migration_service_with_temp_db

        with patch.object(service, "has_pending_migrations", return_value=False):
            with patch.object(service, "db_migration_version", return_value="current"):
                result = service.migrate()

                assert result.migration_version == "current"
                # Verify backup was not created
                backup_path = service._get_pre_migration_backup_path()
                assert not backup_path.exists()

    def test_migrate_creates_backup_before_migration(self, temp_db_engine, temp_db_path, migration_service_with_temp_db):
        """Test that migrate() creates backup before applying migrations."""
        service = migration_service_with_temp_db

        # Ensure database exists and is valid
        assert temp_db_path.exists()
        original_size = temp_db_path.stat().st_size

        backup_path = service._get_pre_migration_backup_path()

        with patch.object(service, "has_pending_migrations", return_value=True):
            with patch.object(service, "apply_migrations") as mock_apply:
                # Track when apply_migrations is called to verify backup exists at that point
                backup_created = False

                def check_backup(*args, **kwargs):
                    nonlocal backup_created
                    backup_created = backup_path.exists()
                    return MagicMock(
                        app_version="0.1.0",
                        migration_version="new_version"
                    )

                mock_apply.side_effect = check_backup

                service.migrate()

                # Verify backup was created before migration was applied
                assert backup_created, "Backup should exist when apply_migrations is called"
                # Verify backup was deleted after successful migration
                assert not backup_path.exists(), "Backup should be deleted after successful migration"

    def test_migrate_deletes_backup_on_success(self, temp_db_engine, temp_db_path, migration_service_with_temp_db):
        """Test that migrate() deletes backup after successful migration."""
        service = migration_service_with_temp_db

        # Ensure database exists
        assert temp_db_path.exists()

        with patch.object(service, "has_pending_migrations", return_value=True):
            with patch.object(service, "apply_migrations") as mock_apply:
                mock_apply.return_value = MagicMock(
                    app_version="0.1.0",
                    migration_version="new_version"
                )

                service.migrate()

                # Verify backup was deleted
                backup_path = service._get_pre_migration_backup_path()
                assert not backup_path.exists()

    def test_migrate_restores_backup_on_failure(self, temp_db_engine, temp_db_path, migration_service_with_temp_db):
        """Test that migrate() restores backup when migration fails."""
        service = migration_service_with_temp_db

        # Ensure database exists and is valid
        assert temp_db_path.exists()
        original_size = temp_db_path.stat().st_size

        with patch.object(service, "has_pending_migrations", return_value=True):
            with patch.object(service, "apply_migrations") as mock_apply:
                # Simulate migration failure
                mock_apply.side_effect = Exception("Migration failed")

                # Mock db_migration_version to avoid database errors after restore
                with patch.object(service, "db_migration_version", return_value="test_version"):
                    with pytest.raises(MigrationFailed):
                        service.migrate()

                # Verify database was restored (same size)
                assert temp_db_path.exists()
                assert temp_db_path.stat().st_size == original_size

                # Backup should still exist (not deleted on failure)
                backup_path = service._get_pre_migration_backup_path()
                assert backup_path.exists()

    def test_migrate_logs_operations(self, temp_db_engine, temp_db_path, migration_service_with_temp_db, caplog):
        """Test that migrate() logs backup operations."""
        service = migration_service_with_temp_db

        # Ensure database exists
        assert temp_db_path.exists()

        with caplog.at_level(logging.INFO):
            with patch.object(service, "has_pending_migrations", return_value=True):
                with patch.object(service, "apply_migrations") as mock_apply:
                    mock_apply.return_value = MagicMock(
                        app_version="0.1.0",
                        migration_version="new_version"
                    )

                    service.migrate()

                    # Check logs
                    log_messages = [record.message for record in caplog.records]
                    assert any("Created pre-migration backup" in msg for msg in log_messages)
                    assert any("Deleted pre-migration backup" in msg for msg in log_messages)

    def test_migrate_logs_no_pending_migrations(self, migration_service_with_temp_db, caplog):
        """Test that migrate() logs when no pending migrations."""
        service = migration_service_with_temp_db

        with caplog.at_level(logging.INFO):
            with patch.object(service, "has_pending_migrations", return_value=False):
                with patch.object(service, "db_migration_version", return_value="current"):
                    service.migrate()

                    log_messages = [record.message for record in caplog.records]
                    assert any("No pending migrations found" in msg for msg in log_messages)


class TestMigrationFailureDialog:
    """Test migration failure dialog integration."""

    def test_migration_failure_raises_exception_with_metadata(self, temp_db_engine, temp_db_path, migration_service_with_temp_db):
        """Test that MigrationFailed exception includes backup metadata."""
        service = migration_service_with_temp_db

        # Ensure database exists
        assert temp_db_path.exists()

        with patch.object(service, "has_pending_migrations", return_value=True):
            with patch.object(service, "apply_migrations") as mock_apply:
                mock_apply.side_effect = Exception("Migration failed")

                # Mock db_migration_version to avoid database errors after restore
                with patch.object(service, "db_migration_version", return_value="test_version"):
                    with pytest.raises(MigrationFailed) as exc_info:
                        service.migrate()

                    # Verify exception has error and metadata
                    assert exc_info.value.error is not None
                    assert isinstance(exc_info.value.error, Exception)
                    assert exc_info.value.backup_migration_version == "test_version"
