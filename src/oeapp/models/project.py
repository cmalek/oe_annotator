"""Project model."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass
class Project:
    """Represents a project."""

    #: The project ID.
    id: int | None
    #: The project name.
    name: str
    #: The date and time the project was created.
    created_at: datetime
    #: The date and time the project was last updated.
    updated_at: datetime
