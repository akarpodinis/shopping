from typing import Any
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.infra.db import engine, ingredients, ingredients_recipes, recipes


def all() -> list[dict[str, Any]]:
    with engine.connect() as conn:
        return [dict(ingredient) for ingredient
                in conn.execute(recipes.select()).mappings().all()]


class RecipeDoesNotExistError(Exception):
    pass


def one(id: UUID) -> dict[str, Any]:
    with engine.connect() as conn:
        recipe = conn.execute(recipes.select().where(recipes.c.id == id)).mappings().first()
        if not recipe:
            raise RecipeDoesNotExistError

        sel = select(ingredients.c.name, ingredients.c.id, ingredients_recipes.c.amount)
        sel = sel.select_from(ingredients
                              .join(ingredients_recipes,
                                    ingredients_recipes.c.ingredient == ingredients.c.id)
                              .join(recipes,
                                    recipes.c.id == ingredients_recipes.c.recipe))
        sel = sel.where(recipes.c.id == id)
        rows = conn.execute(sel).mappings().all()

        return {
            'id': recipe.id,
            'name': recipe.name,
            'ingredients': [dict(row) for row in rows]
        }


class DuplicateRecipeError(Exception):
    pass


# TODO rename to "add(...)"
def insert(name: str, ingredients: list[tuple[UUID, int]]) -> UUID:
    try:
        with engine.connect() as conn:
            # Insert the base recipe record, raising if there's a duplicate name
            inserted = conn.execute(
                recipes.insert().values(
                    name=name
                ).returning(
                    recipes.c.id
                )
            ).mappings().first()

            # Insert the join records with amounts included
            for ingredient in ingredients:
                conn.execute(
                    ingredients_recipes.insert().values(
                        recipe=inserted.id,
                        ingredient=ingredient[0],
                        amount=ingredient[1]
                    )
                )
            conn.commit()
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise DuplicateRecipeError
        else:
            raise

    return inserted.id


def stocked(ids: list[UUID]) -> list[tuple[UUID, str]]:
    with engine.connect() as conn:
        stocked = conn.execute(
            select(ingredients.c.id, ingredients.c.name).distinct()
            .join(ingredients_recipes, ingredients_recipes.c.ingredient == ingredients.c.id)
            .join(recipes, recipes.c.id == ingredients_recipes.c.recipe)
            .where(ingredients.c.stocked)
            .where(recipes.c.id.in_(ids))
        ).mappings().all()
    return [(stock.id, stock.name) for stock in stocked]
