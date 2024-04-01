from typing import Any, Optional
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.infra.db import engine, ingredients


def all() -> list[dict[str, Any]]:
    with engine.connect() as conn:
        return [dict(ingredient) for ingredient
                in conn.execute(ingredients.select()).mappings().all()]


def one(id: UUID) -> Optional[dict[str, Any]]:
    with engine.connect() as conn:
        ingredient = conn.execute(
            select(ingredients).where(ingredients.c.id == id)).mappings().first()
        return dict(ingredient) if ingredient else None


class DuplicateIngredientError(Exception):
    pass


def insert(name: str, aisle: str, stocked: bool) -> None:
    try:
        with engine.connect() as conn:
            conn.execute(
                ingredients.insert().values(
                    name=name,
                    aisle=aisle,
                    stocked=stocked
                )
            )
            conn.commit()
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise DuplicateIngredientError
        else:
            raise


def delete(id: UUID) -> None:
    with engine.connect() as conn:
        conn.execute(
            ingredients.delete().where(ingredients.c.id == id)
        )
        conn.commit()


def template_configuration() -> dict[str, Any]:
    return {
        'fields': [
            ingredients.c.name.name,
            ingredients.c.aisle.name,
            ingredients.c.stocked.name
        ],
        'types': [
            'text', 'text', 'checkbox'
        ],
        'required': [
            'required', 'required', ''
        ]
    }
