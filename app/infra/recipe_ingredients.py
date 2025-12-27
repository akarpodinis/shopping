from uuid import UUID

from sqlalchemy import select

from app.infra import Recipe
from app.infra.db import engine, ingredients_recipes, recipes


def recipes_using(ingredient: UUID) -> list[Recipe]:
    with engine.connect() as conn:
        return [Recipe(**recipe) for recipe in conn.execute(
            select(recipes)
            .join(ingredients_recipes, ingredients_recipes.c.recipe == recipes.c.id)
            .where(ingredients_recipes.c.ingredient == ingredient)
        ).mappings().all()]
