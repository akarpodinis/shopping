from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, label, or_, select
from sqlalchemy.dialects.postgresql import insert

from app.infra.db import (
    engine, ingredients, ingredients_recipes, lists, list_items, list_recipes, recipes
)


def add(date: datetime, recipe_scales: dict[UUID, float], included_ingredients: list[UUID],
        arbitrary_items: list[tuple[str, str, int]]) -> UUID:
    with engine.connect() as conn:
        # Create the base list item
        list_id = conn.execute(
            lists.insert().values(
                date=date
            ).returning(lists.c.id)
        ).mappings().first().id

        # Get all the selected recipes
        chosen_recipes = conn.execute(
            recipes.select().where(recipes.c.id.in_(recipe_scales.keys()))
        ).mappings().all()

        # Create the historical recipe information
        conn.execute(
            insert(list_recipes), [
                {
                    'list': list_id,
                    'name': recipe.name,
                    'scale': recipe_scales[recipe.id]
                } for recipe in chosen_recipes]
        )

        # Get all the ingredients for each recipe to scale including stocked
        """
        select i.id, i.name, i.aisle, ceil(ir.amount * 1.2) from ingredients i
        join ingredients_recipes as ir on ir.ingredient = i.id
        join recipes as r on r.id = ir.recipe
        where r.id = '4ac6244d-4a42-436a-894e-c4165ac1f78a'
            and (not i.stocked or i.id in ('043233c5-e720-4e0e-9110-01914b379b5b'))
        group by i.id, i.name, i.aisle, ir.amount, i.stocked
        order by i.aisle desc;
        """
        desired_ingredients = {}
        for recipe in recipe_scales.keys():
            resolved_ingredients = conn.execute(
                select(
                    ingredients.c.id,
                    ingredients.c.name,
                    ingredients.c.aisle,
                    label('amount', func.ceil(ingredients_recipes.c.amount * recipe_scales[recipe]))
                )
                .join(ingredients_recipes, ingredients_recipes.c.ingredient == ingredients.c.id)
                .join(recipes, recipes.c.id == ingredients_recipes.c.recipe)
                .where(recipes.c.id == recipe)
                .where(or_(~ingredients.c.stocked, ingredients.c.id.in_(included_ingredients)))
                .group_by(
                    ingredients.c.id,
                    ingredients.c.name,
                    ingredients.c.aisle,
                    ingredients_recipes.c.amount
                )
            ).mappings().all()

        # Combine the ingredient amounts by ID
        for ingredient in resolved_ingredients:
            if ingredient.id in desired_ingredients:
                desired_ingredients[ingredient.id]['amount'] += ingredient.amount
            else:
                desired_ingredients[ingredient.id] = ingredient

        # Create the historical list ingredient item information
        conn.execute(
            insert(list_items), [
                {
                    'list': list_id,
                    'name': desired_ingredient['name'],
                    'aisle': desired_ingredient['aisle'],
                    'amount': desired_ingredient['amount']
                } for desired_ingredient in desired_ingredients.values()]
        )

        # Create the historical list arbitrary item information
        if arbitrary_items:
            # We need an if here because conn.execute(...) will be called even if arbitrary_items
            # is empty, resulting in attempting to insert a null series of values.
            conn.execute(
                insert(list_items), [
                    {
                        'list': list_id,
                        'name': arbitrary_item[0],
                        'aisle': arbitrary_item[1],
                        'amount': arbitrary_item[2]
                    } for arbitrary_item in arbitrary_items]
            )

        conn.commit()

    return list_id


@dataclass
class ShoppingListItem:
    name: str
    amount: int


@dataclass
class ShoppingListAisle:
    name: str
    items: list[ShoppingListItem]


@dataclass
class ShoppingList:
    date: datetime
    aisles: list[ShoppingListAisle]


def for_shopping(id: UUID) -> ShoppingList:
    with engine.connect() as conn:
        shopping_items = conn.execute(
            select(list_items.c.name, list_items.c.aisle, list_items.c.amount)
            .join(list_items, list_items.c.list == id)
            .where(lists.c.id == id)).mappings().all()
        list_date = conn.execute(
            select(lists.c.date).where(lists.c.id == id)
        ).mappings().one().date

        aisles = {}

        for item in shopping_items:
            new_list_item = ShoppingListItem(item.name, item.amount)
            if item.aisle not in aisles:
                aisles[item.aisle] = ShoppingListAisle(item.aisle, [new_list_item])
            else:
                aisles[item.aisle].items += [new_list_item]

    return ShoppingList(list_date, list(aisles.values()))
