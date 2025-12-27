from dataclasses import dataclass
from uuid import UUID


@dataclass
class Recipe:
    id: UUID
    name: str
    routine: bool
    servings: int
