"""Unit tests for Project model."""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from oeapp.exc import AlreadyExists
from oeapp.models.project import Project
from oeapp.models.sentence import Sentence


class TestProject:
    """Test cases for Project model."""

    def test_create_model(self, db_session):
        """Test model creation."""
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.commit()

        assert project.id is not None
        assert project.name == "Test Project"
        assert isinstance(project.created_at, datetime)
        assert isinstance(project.updated_at, datetime)

    def test_exists_returns_true_when_exists(self, db_session):
        """Test exists() returns True when project exists."""
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.commit()

        assert Project.exists(db_session, "Test Project") is True

    def test_exists_returns_false_when_not_exists(self, db_session):
        """Test exists() returns False when project doesn't exist."""
        assert Project.exists(db_session, "Nonexistent") is False

    def test_get_returns_existing(self, db_session):
        """Test get() returns existing project."""
        project = Project(name="Test Project")
        db_session.add(project)
        db_session.commit()
        project_id = project.id

        retrieved = Project.get(db_session, project_id)
        assert retrieved is not None
        assert retrieved.id == project_id
        assert retrieved.name == "Test Project"

    def test_get_returns_none_for_nonexistent(self, db_session):
        """Test get() returns None for nonexistent project."""
        result = Project.get(db_session, 99999)
        assert result is None

    def test_first_returns_first_project(self, db_session):
        """Test first() returns first project."""
        project1 = Project(name="First Project")
        project2 = Project(name="Second Project")
        db_session.add(project1)
        db_session.add(project2)
        db_session.commit()

        first = Project.first(db_session)
        assert first is not None
        assert first.name in ["First Project", "Second Project"]

    def test_first_returns_none_when_no_projects(self, db_session):
        """Test first() returns None when no projects exist."""
        result = Project.first(db_session)
        assert result is None

    def test_list_returns_all_projects(self, db_session):
        """Test list() returns all projects."""
        project1 = Project(name="Project 1")
        project2 = Project(name="Project 2")
        db_session.add(project1)
        db_session.add(project2)
        db_session.commit()

        projects = Project.list(db_session)
        assert len(projects) == 2
        assert all(isinstance(p, Project) for p in projects)

    def test_list_returns_empty_when_no_projects(self, db_session):
        """Test list() returns empty list when no projects exist."""
        projects = Project.list(db_session)
        assert projects == []

    def test_create_creates_project_with_sentences(self, db_session):
        """Test create() creates project and sentences from text."""
        project = Project.create(
            session=db_session, text="Se cyning. Þæt scip.", name="Test Project"
        )

        assert project.id is not None
        assert project.name == "Test Project"
        assert len(project.sentences) == 2
        # Sentence splitter includes punctuation
        assert project.sentences[0].text_oe == "Se cyning."
        assert project.sentences[1].text_oe == "Þæt scip."

    def test_create_raises_already_exists_for_duplicate_name(self, db_session):
        """Test create() raises AlreadyExists for duplicate name."""
        Project.create(session=db_session, text="Se cyning", name="Test Project")
        db_session.commit()

        with pytest.raises(AlreadyExists):
            Project.create(session=db_session, text="Þæt scip", name="Test Project")

    def test_create_with_default_name(self, db_session):
        """Test create() uses default name when not provided."""
        project = Project.create(session=db_session, text="Se cyning")
        assert project.name == "Untitled Project"

    def test_total_token_count_returns_count(self, db_session):
        """Test total_token_count() returns total tokens in project."""
        project = Project.create(
            session=db_session, text="Se cyning. Þæt scip.", name="Test"
        )
        db_session.commit()

        count = project.total_token_count(db_session)
        assert count > 0
        # Should have tokens from both sentences
        assert count >= 4  # At least "Se", "cyning", "Þæt", "scip"

    def test_total_token_count_returns_zero_for_empty(self, db_session):
        """Test total_token_count() returns 0 for project with no sentences."""
        project = Project(name="Empty Project")
        db_session.add(project)
        db_session.commit()

        count = project.total_token_count(db_session)
        assert count == 0

    def test_delete_removes_project(self, db_session):
        """Test deleting project removes it."""
        project = Project.create(session=db_session, text="Se cyning", name="To Delete")
        db_session.commit()
        project_id = project.id

        db_session.delete(project)
        db_session.commit()

        assert Project.get(db_session, project_id) is None

    def test_delete_removes_cascade_sentences(self, db_session):
        """Test deleting project cascades to sentences."""
        project = Project.create(session=db_session, text="Se cyning", name="Test")
        db_session.commit()
        sentence_id = project.sentences[0].id

        db_session.delete(project)
        db_session.commit()

        # Sentence should be deleted via cascade
        sentence = db_session.get(Sentence, sentence_id)
        assert sentence is None

    def test_append_oe_text_appends_sentences(self, db_session):
        """Test append_oe_text() appends sentences to project."""
        project = Project.create(session=db_session, text="Se cyning", name="Test")
        db_session.commit()
        original_count = len(project.sentences)

        project.append_oe_text(db_session, "Þæt scip.")
        db_session.refresh(project)

        assert len(project.sentences) == original_count + 1
        # Sentence splitter includes punctuation
        assert project.sentences[-1].text_oe == "Þæt scip."

    def test_append_oe_text_to_empty_project(self, db_session):
        """Test append_oe_text() works on project with no sentences."""
        project = Project(name="Empty Project")
        db_session.add(project)
        db_session.commit()

        project.append_oe_text(db_session, "Se cyning.")
        db_session.refresh(project)

        assert len(project.sentences) == 1
        # Sentence splitter includes punctuation
        assert project.sentences[0].text_oe == "Se cyning."

    def test_to_json_serializes_project(self, db_session):
        """Test to_json() serializes project data."""
        project = Project.create(session=db_session, text="Se cyning", name="Test")
        db_session.commit()

        data = project.to_json()
        assert data["name"] == "Test"
        assert "created_at" in data
        assert "updated_at" in data

    def test_from_json_creates_project(self, db_session):
        """Test from_json() creates project from data."""
        project_data = {
            "name": "Imported Project",
            "created_at": "2024-01-15T10:30:45+00:00",
            "updated_at": "2024-01-15T10:30:45+00:00",
        }
        project = Project.from_json(db_session, project_data, "Imported Project")
        db_session.commit()

        assert project.name == "Imported Project"
        assert project.id is not None

    def test_unique_constraint_prevents_duplicate_names(self, db_session):
        """Test unique constraint prevents duplicate project names."""
        project1 = Project(name="Duplicate")
        db_session.add(project1)
        db_session.commit()

        project2 = Project(name="Duplicate")
        db_session.add(project2)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_created_at_set_on_creation(self, db_session):
        """Test created_at is set on creation."""
        before = datetime.now()
        project = Project(name="Test")
        db_session.add(project)
        db_session.commit()
        after = datetime.now()

        assert before <= project.created_at <= after

    def test_updated_at_updates_on_change(self, db_session):
        """Test updated_at updates when project is modified."""
        project = Project(name="Test")
        db_session.add(project)
        db_session.commit()
        original_updated = project.updated_at

        import time

        time.sleep(0.01)

        project.name = "Updated"
        db_session.commit()
        db_session.refresh(project)

        assert project.updated_at > original_updated

    def test_relationship_with_sentences(self, db_session):
        """Test project has relationship with sentences."""
        project = Project.create(session=db_session, text="Se cyning", name="Test")
        db_session.commit()

        assert len(project.sentences) > 0
        assert all(s.project_id == project.id for s in project.sentences)

