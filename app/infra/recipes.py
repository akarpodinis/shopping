from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select

from app.infra.db import engine, recipes


def all() -> list[dict[str, Any]]:
    with engine.connect() as conn:
        return [dict(ingredient) for ingredient
                in conn.execute(recipes.select()).mappings().all()]


def one(id: UUID) -> Optional[dict[str, Any]]:
    with engine.connect() as conn:
        ingredient = conn.execute(
            select(recipes).where(recipes.c.id == id)).mappings().first()
        return dict(ingredient) if ingredient else None
