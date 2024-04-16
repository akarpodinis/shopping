from dataclasses import dataclass
from typing import Any
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from app.infra.db import engine, ingredients, ingredients_recipes, recipe_notes, recipes


@dataclass
class Recipe:
    id: UUID
    name: str
    servings: int
    routine: bool


def all() -> list[Recipe]:
    with engine.connect() as conn:
        return [Recipe(**recipe) for recipe
                in conn.execute(recipes.select()).mappings().all()]


class RecipeDoesNotExistError(Exception):
    pass


def update(id: UUID, name: str, routine: bool, servings: int, ingredients: list[tuple[UUID, int]],
           notes: str) -> None:
    try:
        with engine.connect() as conn:
            # Update the base record
            conn.execute(
                recipes.update().values(
                    name=name,
                    servings=servings,
                    routine=routine
                ).where(recipes.c.id == id)
            )

            # Update notes with ON CONFLICT ... DO UPDATE
            conn.execute(
                insert(recipe_notes).values(
                    recipe=id,
                    notes=notes
                ).on_conflict_do_update(
                    index_elements=[recipe_notes.c.recipe],
                    set_={
                        recipe_notes.c.notes: notes
                    }
                )
            )

            # Update the linked ingredients
            for ingredient in ingredients:
                conn.execute(
                    ingredients_recipes.update().values(
                        amount=ingredient[1]
                    ).where(ingredients_recipes.c.ingredient == ingredient[0])
                )

            conn.commit()
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise DuplicateRecipeError
        else:
            raise


@dataclass
class EditableIngredient:
    id: str
    name: str
    amount: int


@dataclass
class EditableRecipe(Recipe):
    ingredients: list[EditableIngredient]
    notes: str


def editable(id: UUID) -> EditableRecipe:
    with engine.connect() as conn:
        recipe = conn.execute(
            recipes.select()
            .where(recipes.c.id == id)
        ).mappings().first()

        notes = conn.execute(
            select(recipe_notes.c.notes)
            .where(recipe_notes.c.recipe == id)
        ).scalar()

        """
        select i.name, i.stocked, ir.amount from recipes r
        join ingredients_recipes as ir on ir.recipe = r.id
        join ingredients as i on i.id = ir.ingredient
        where r.id = '86a37f9c-fbf7-426f-a54a-0eff25c26e18';
        """
        recipe_ingredients = conn.execute(
            select(
                ingredients.c.id,
                ingredients.c.name,
                ingredients.c.stocked,
                ingredients_recipes.c.amount)
            .join(ingredients_recipes, ingredients_recipes.c.recipe == recipes.c.id)
            .join(ingredients, ingredients.c.id == ingredients_recipes.c.ingredient)
            .where(recipes.c.id == id)
        ).mappings().all()

    return EditableRecipe(
        recipe.id,
        recipe.name,
        recipe.routine,
        recipe.servings,
        [EditableIngredient(ingredient.id, ingredient.name, ingredient.amount)
         for ingredient in recipe_ingredients],
        notes)


class DuplicateRecipeError(Exception):
    pass


def add(name: str, routine: bool, servings: int, ingredients: list[tuple[UUID, int]]) -> UUID:
    try:
        with engine.connect() as conn:
            # Insert the base recipe record, raising if there's a duplicate name
            inserted = conn.execute(
                recipes.insert().values(
                    name=name,
                    routine=routine,
                    servings=servings
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


def stocked(ids: list[UUID]) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        stocked = conn.execute(
            select(ingredients.c.id, ingredients.c.name).distinct()
            .join(ingredients_recipes, ingredients_recipes.c.ingredient == ingredients.c.id)
            .join(recipes, recipes.c.id == ingredients_recipes.c.recipe)
            .where(ingredients.c.stocked)
            .where(recipes.c.id.in_(ids))
        ).mappings().all()
    return [dict(stock) for stock in stocked]
