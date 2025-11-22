"""Project import/export service for Old English Annotator."""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import select

from oeapp.db import (
    get_current_code_migration_version,
    get_current_db_migration_version,
    get_min_version_for_migration,
)
from oeapp.models.project import Project
from oeapp.models.sentence import Sentence

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _get_migration_chain(from_version: str, to_version: str) -> list[str]:
    """
    Get ordered list of migration revision IDs from one version to another.

    Args:
        from_version: Starting migration version (export version)
        to_version: Target migration version (current version)

    Returns:
        Ordered list of migration revision IDs (from oldest to newest)

    """
    alembic_ini_path = Path(__file__).parent.parent / "etc" / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    script = ScriptDirectory.from_config(alembic_cfg)

    # Build a map of down_revision -> list of revisions that have it
    # This allows us to walk forward from from_version to to_version
    forward_map: dict[str | None, list[str]] = {}
    revision_to_down: dict[str, str | None] = {}

    for script_revision in script.walk_revisions():
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


class ProjectExporter:
    """Exports projects to JSON format."""

    def __init__(self, session: Session) -> None:
        """
        Initialize exporter.

        Args:
            session: SQLAlchemy session

        """
        self.session = session

    def export_project(self, project_id: int) -> dict[str, Any]:
        """
        Export project to a dictionary (without PKs).

        Args:
            project_id: Project ID to export

        Returns:
            Dictionary containing project data

        """
        project = self.session.get(Project, project_id)
        if project is None:
            msg = f"Project with ID {project_id} not found"
            raise ValueError(msg)

        # Get migration version
        migration_version = get_current_db_migration_version()

        # Serialize project without PKs
        project_data: dict[str, Any] = {
            "export_version": "1.0",
            "migration_version": migration_version,
            "project": project.to_json(),
            "sentences": [],
        }

        # Sort sentences by display_order
        sentences = sorted(project.sentences, key=lambda s: s.display_order)

        for sentence in sentences:
            sentence_data = sentence.to_json(self.session)
            project_data["sentences"].append(sentence_data)

        return project_data


class ProjectImportProcessor:
    """Processes project import data and creates database entities."""

    def __init__(self, session: Session) -> None:
        """
        Initialize processor.

        Args:
            session: SQLAlchemy session

        """
        self.session = session

    def _validate_migration_version(self, export_version: str) -> None:
        """
        Validate that the export migration version is compatible.

        Args:
            export_version: Migration version from export

        Raises:
            ValueError: If migration version is incompatible

        """
        if not export_version:
            msg = "Export file missing migration_version"
            raise ValueError(msg)

        current_code_version = get_current_code_migration_version()

        if not current_code_version:
            return

        # If versions match, no transformation needed
        if export_version == current_code_version:
            return

        # Check if we can build a migration chain from export to current
        try:
            migration_chain = _get_migration_chain(export_version, current_code_version)
            # If chain is empty and versions don't match, migration might not exist
            if not migration_chain and export_version != current_code_version:
                min_version = get_min_version_for_migration(export_version)
                if min_version:
                    msg = (
                        f"This export requires at least version {min_version} of the "
                        f"application. Please upgrade to version {min_version} or "
                        "later to import this project."
                    )
                    raise ValueError(msg)  # noqa: TRY301
                msg = (
                    f"Migration version {export_version} is not compatible with "
                    f"the current application version {current_code_version}."
                )
                raise ValueError(msg)  # noqa: TRY301
        except ValueError:
            # Re-raise ValueError as-is
            raise
        except Exception as e:
            # If we can't build chain, check minimum version
            min_version = get_min_version_for_migration(export_version)
            if min_version:
                msg = (
                    f"This export requires at least version {min_version} of the "
                    f"application. Please upgrade to version {min_version} or "
                    "later to import this project."
                )
                raise ValueError(msg) from e
            msg = (
                f"Migration version {export_version} is not compatible with "
                f"the current application version."
            )
            raise ValueError(msg) from e

    def _transform_data(
        self, data: dict[str, Any], export_version: str
    ) -> dict[str, Any]:
        """
        Transform data by applying field mappings if needed.

        Args:
            data: Project data dictionary
            export_version: Migration version from export

        Returns:
            Transformed data dictionary

        """
        current_code_version = get_current_code_migration_version()

        if export_version == current_code_version or not current_code_version:
            return data

        try:
            migration_chain = _get_migration_chain(export_version, current_code_version)
            if migration_chain:
                data = self._apply_field_mappings(data, migration_chain)
        except Exception:
            # If we can't get chain, proceed without field mapping
            # Compatibility was already checked in _validate_migration_version
            pass

        return data

    def _load_field_mappings(self) -> dict[str, dict[str, dict[str, str]]]:
        """
        Load field mappings from JSON file.

        Returns:
            Dictionary mapping migration SHA to model field mappings

        """
        field_mappings_path = (
            Path(__file__).parent.parent / "etc" / "field_mappings.json"
        )
        if not field_mappings_path.exists():
            return {}

        try:
            with field_mappings_path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, PermissionError, json.JSONDecodeError):
            return {}

    def _apply_field_mappings(
        self, data: dict[str, Any], migration_chain: list[str]
    ) -> dict[str, Any]:
        """
        Apply field mappings incrementally through migration chain.

        Args:
            data: Data dictionary to transform
            migration_chain: Ordered list of migration revision IDs

        Returns:
            Transformed data dictionary

        """
        field_mappings = self._load_field_mappings()

        # Apply mappings for each migration in order
        for migration_sha in migration_chain:
            if migration_sha not in field_mappings:
                continue

            migration_mappings = field_mappings[migration_sha]
            self._apply_mappings_recursive(data, migration_mappings)

        return data

    def _apply_mappings_recursive(
        self, obj: Any, mappings: dict[str, dict[str, str]]
    ) -> None:
        """
        Recursively apply field mappings to data structure.

        Args:
            obj: Object to transform (dict, list, or primitive)
            mappings: Field mappings for models

        """
        if isinstance(obj, dict):
            for field_mapping in mappings.values():
                for old_field, new_field in field_mapping.items():
                    if old_field in obj:
                        # Rename the field
                        obj[new_field] = obj.pop(old_field)

            # Recursively process nested structures
            for value in obj.values():
                self._apply_mappings_recursive(value, mappings)

        elif isinstance(obj, list):
            for item in obj:
                self._apply_mappings_recursive(item, mappings)

    def _resolve_project_name(self, name: str) -> tuple[str, bool]:
        """
        Resolve project name collision by appending number.

        Args:
            name: Original project name

        Returns:
            Tuple of (resolved_name, was_renamed)

        """
        original_name = name
        counter = 1
        was_renamed = False

        while True:
            existing = self.session.scalar(select(Project).where(Project.name == name))
            if existing is None:
                break
            name = f"{original_name} ({counter})"
            counter += 1
            was_renamed = True

        return name, was_renamed

    def _create_project(self, project_data: dict[str, Any]) -> tuple[Project, bool]:
        """
        Create project entity from data.

        Args:
            project_data: Project data dictionary

        Returns:
            Tuple of (created Project entity, was_renamed)

        """
        resolved_name, was_renamed = self._resolve_project_name(project_data["name"])
        project = Project.from_json(self.session, project_data, resolved_name)
        return project, was_renamed

    def _create_sentence(self, project_id: int, sentence_data: dict[str, Any]) -> None:
        """
        Create sentence and all related entities (tokens, annotations, notes).

        Args:
            project_id: Project ID to attach sentence to
            sentence_data: Sentence data dictionary

        """
        Sentence.from_json(self.session, project_id, sentence_data)

    def process_import(self, data: dict[str, Any]) -> tuple[Project, bool]:
        """
        Process project import from data dictionary.

        Args:
            data: Project data dictionary

        Returns:
            Tuple of (imported_project, was_renamed)

        Raises:
            ValueError: If migration version is incompatible

        """
        # Validate migration version
        export_version = data.get("migration_version")
        self._validate_migration_version(export_version or "")

        # Transform data if needed
        data = self._transform_data(data, export_version or "")

        # Create project
        project, was_renamed = self._create_project(data["project"])

        # Create sentences and all related entities
        for sentence_data in data["sentences"]:
            self._create_sentence(project.id, sentence_data)

        self.session.commit()
        return project, was_renamed


class ProjectImporter:
    """Imports projects from JSON format."""

    def __init__(self, session: Session) -> None:
        """
        Initialize importer.

        Args:
            session: SQLAlchemy session

        """
        self.session = session

    def import_project(self, data: dict[str, Any]) -> tuple[Project, bool]:
        """
        Import project from dictionary.

        Args:
            data: Project data dictionary

        Returns:
            Tuple of (imported_project, was_renamed)

        Raises:
            ValueError: If migration version is incompatible

        """
        processor = ProjectImportProcessor(self.session)
        return processor.process_import(data)
