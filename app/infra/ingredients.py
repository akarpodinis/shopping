from dataclasses import dataclass
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.infra.db import engine, ingredients


@dataclass
class Ingredient:
    id: UUID
    name: str
    aisle: str
    stocked: bool


def all() -> list[Ingredient]:
    with engine.connect() as conn:
        return [Ingredient(**ingredient) for ingredient
                in conn.execute(ingredients.select()).mappings().all()]


class IngredientNotFoundError(Exception):
    pass


def one(id: UUID) -> Ingredient:
    with engine.connect() as conn:
        ingredient = conn.execute(
            select(ingredients).where(ingredients.c.id == id)).mappings().first()

        if not ingredient:
            raise IngredientNotFoundError

        return Ingredient(**ingredient)


class DuplicateIngredientError(Exception):
    pass


def add(name: str, aisle: str, stocked: bool) -> UUID:
    try:
        with engine.connect() as conn:
            inserted = conn.execute(
                ingredients.insert().values(
                    name=name,
                    aisle=aisle,
                    stocked=stocked
                ).returning(
                    ingredients.c.id
                )
            ).mappings().first()
            conn.commit()
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise DuplicateIngredientError
        else:
            raise
    return inserted.id


def delete(id: UUID) -> None:
    with engine.connect() as conn:
        conn.execute(
            ingredients.delete().where(ingredients.c.id == id)
        )
        conn.commit()


def names_and_ids() -> tuple[list[str], list[UUID]]:
    names = []
    ids = []
    with engine.connect() as conn:
        for ingredient in conn.execute(select(ingredients.c.name, ingredients.c.id)).all():
            names.append(ingredient.name)
            ids.append(ingredient.id)

    return names, ids


def update(id: UUID, stocked: bool, name: str = None, aisle: str = None) -> Ingredient:
    with engine.connect() as conn:
        try:
            values = {}
            if name:
                values['name'] = name
            if aisle:
                values['aisle'] = aisle
            values['stocked'] = stocked
            updated = conn.execute(
                ingredients.update().values(**values).where(ingredients.c.id == id)
                .returning(ingredients)
            ).mappings().first()
            conn.commit()
        except IntegrityError as e:
            if isinstance(e.orig, UniqueViolation):
                raise DuplicateIngredientError
            else:
                raise

        return Ingredient(**updated)
