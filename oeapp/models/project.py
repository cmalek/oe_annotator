"""Project model."""

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from oeapp.exc import AlreadyExists, DoesNotExist
from oeapp.models.sentence import Sentence
from oeapp.services.splitter import split_sentences

if TYPE_CHECKING:
    import builtins
    from datetime import datetime

    from oeapp.services.db import Database


@dataclass
class Project:
    """
    Represents a project.
    """

    #: The project ID.
    id: int | None
    #: The project name.
    name: str
    #: The date and time the project was created.
    created_at: datetime
    #: The date and time the project was last updated.
    updated_at: datetime
    #: The Database object for the project.
    db: Database

    @property
    def sentences(self) -> list[Sentence]:
        """
        Get the sentences for the project.
        """
        return Sentence.list(self.db, cast("int", self.id))

    @classmethod
    def create(cls, db: Database, text: str, name: str = "Untitled Project") -> Project:
        """
        Create a new project.

        Args:
            db: Database object
            text: Old English text to process and add to the project

        Keyword Args:
            name: Project name

        Returns:
            The new :class:`~oeapp.models.project.Project` object

        """
        cursor = db.cursor
        if cursor.execute("SELECT * FROM projects WHERE name = ?", (name,)).fetchone():
            raise AlreadyExists("Project", name)  # noqa: EM101
        cursor.execute("INSERT INTO projects (name) VALUES (?)", (name,))
        project_id = cursor.lastrowid
        if not project_id:
            msg = "Failed to create project"
            raise ValueError(msg)
        db.commit()

        # Fetch the created project to get all fields
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()

        # Load sentences into the project
        sentences_text = split_sentences(text)
        for order, sentence_text in enumerate(sentences_text, 1):
            Sentence.create(
                db=db,
                project_id=project_id,
                display_order=order,
                text_oe=sentence_text,
            )
        return cls(
            id=row["id"],
            name=row["name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            db=db,
        )

    @classmethod
    def get(cls, db: Database, project_id: int) -> Project:
        """
        Get a project by ID.

        Args:
            db: Database object
            project_id: Project ID

        Returns:
            The :class:`~oeapp.models.project.Project` object

        Raises:
            ValueError: If project not found

        """
        cursor = db.cursor
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        if not row:
            raise DoesNotExist("Project", project_id)  # noqa: EM101
        return cls(
            id=row["id"],
            name=row["name"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            db=db,
        )

    @classmethod
    def list(cls, db: Database) -> builtins.list[Project]:
        """
        List all projects in the database.

        Args:
            db: Database object

        Returns:
            List of :class:`~oeapp.models.project.Project` objects

        """
        cursor = db.cursor
        cursor.execute("SELECT * FROM projects ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        return [
            cls(
                db=db,
                id=row["id"],
                name=row["name"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def save(self) -> None:
        """
        Save the project to the database.
        """
        cursor = self.db.cursor
        cursor.execute(
            "UPDATE projects SET name = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (self.name, self.id),
        )
        for sentence in self.sentences:
            sentence.save()
        self.db.commit()
