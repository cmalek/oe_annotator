"""Shared pytest fixtures and test helpers for Ænglisc Toolkit tests."""

import os
import tempfile
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy import select

from oeapp.db import Base
from oeapp.models.project import Project
from oeapp.models.sentence import Sentence
from oeapp.models.token import Token


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for testing PySide6 widgets."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def db_session():
    """Create a temporary database and session for testing."""
    temp_db = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".db")
    temp_db.close()
    db_path = Path(temp_db.name)

    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    engine.dispose()
    os.unlink(temp_db.name)


@pytest.fixture
def sample_project(db_session):
    """Create a sample project with default text."""
    project = Project.create(
        session=db_session,
        text="Se cyning",
        name=f"Sample Project {id(db_session)}",
    )
    db_session.commit()
    return project


@pytest.fixture
def sample_sentence(db_session, sample_project):
    """Create a sample sentence with tokens."""
    sentence = Sentence.create(
        session=db_session,
        project_id=sample_project.id,
        display_order=1,
        text_oe="Se cyning",
    )
    db_session.commit()
    return sentence


# Test helper functions (not fixtures, but available for import)


def create_test_project(session, name=None, text=""):
    """
    Helper to create a project with defaults.

    Args:
        session: SQLAlchemy session
        name: Project name (if None, generates unique name)
        text: Old English text (defaults to empty to avoid creating sentences)

    Returns:
        Created Project instance
    """
    if name is None:
        name = f"Test Project {id(session)}"
    project = Project.create(session=session, text=text, name=name)
    session.commit()
    return project


def create_test_sentence(
    session, project_id=None, text="Se cyning", display_order=1, is_paragraph_start=False
):
    """
    Helper to create a sentence with defaults.

    Args:
        session: SQLAlchemy session
        project_id: Project ID (if None, creates a new project)
        text: Old English text
        display_order: Display order (will be incremented if conflict exists)
        is_paragraph_start: Whether sentence starts a paragraph

    Returns:
        Created Sentence instance
    """
    # If project_id not specified, create a new project
    if project_id is None:
        project = create_test_project(session, name=f"Test Project {id(session)}")
        project_id = project.id

    # Check if a sentence with this display_order already exists
    existing = session.scalar(
        select(Sentence).where(
            Sentence.project_id == project_id,
            Sentence.display_order == display_order
        )
    )
    if existing is not None:
        # Find the next available display_order
        all_sentences = Sentence.list(session, project_id)
        if all_sentences:
            display_order = max(s.display_order for s in all_sentences) + 1
        else:
            display_order = 1

    sentence = Sentence.create(
        session=session,
        project_id=project_id,
        display_order=display_order,
        text_oe=text,
        is_paragraph_start=is_paragraph_start,
    )
    session.commit()
    return sentence


def create_test_token(session, sentence_id, surface="cyning", order_index=0, lemma=None):
    """
    Helper to create a token with defaults.

    Args:
        session: SQLAlchemy session
        sentence_id: Sentence ID
        surface: Token surface form
        order_index: Order index in sentence
        lemma: Optional lemma

    Returns:
        Created Token instance
    """
    token = Token(
        sentence_id=sentence_id,
        order_index=order_index,
        surface=surface,
        lemma=lemma,
    )
    session.add(token)
    session.commit()
    return token

