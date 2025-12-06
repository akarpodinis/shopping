from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, label, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Connection

from app.infra.db import (
    engine, ingredients, ingredients_recipes, list_items, list_recipes, lists, recipes
)


@dataclass
class DisplayableDate:
    date: datetime

    @property
    def display_date(self) -> str:
        return datetime.strftime(self.date, r'%A, %B %-d')


@dataclass
class List(DisplayableDate):
    id: UUID


def all() -> list[List]:
    with engine.connect() as conn:
        all_lists = conn.execute(lists.select().order_by(lists.c.date.desc())).mappings().all()

    return [List(**one_list) for one_list in all_lists]


@dataclass
class HistoricalList(DisplayableDate):
    name: str


def past_recipes(count: int) -> list[HistoricalList]:
    with engine.connect() as conn:
        """select distinct on (lr.name) l.date, lr.name from lists_recipes lr
            join lists as l on l.id = lr.list
            order by lr.name, l.date desc;
        """
        query = select(list_recipes.c.name, lists.c.date).distinct(list_recipes.c.name) \
            .join(lists, lists.c.id == list_recipes.c.list) \
            .order_by(list_recipes.c.name) \
            .order_by(lists.c.date.desc())

        if count > 0:
            query = query.limit(count)

        past_recipes = conn.execute(query).mappings().all()

    return [HistoricalList(**recipe) for recipe in past_recipes]


def add_recipe_items(list_id: UUID,
                     recipe_scales: dict[UUID, float],
                     included_ingredients: list[UUID],
                     conn: Connection) -> None:
    if not recipe_scales:
        return

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
    resolved_ingredients = []
    for recipe in recipe_scales.keys():
        resolved_ingredients += conn.execute(
            select(
                ingredients.c.id,
                ingredients.c.name,
                ingredients.c.aisle,
                label('amount', (ingredients_recipes.c.amount * recipe_scales[recipe]))
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
    for resolved_ingredient in resolved_ingredients:
        ingredient = dict(resolved_ingredient)
        if ingredient['id'] in desired_ingredients:
            desired_ingredients[ingredient['id']]['amount'] += ingredient['amount']
        else:
            desired_ingredients[ingredient['id']] = ingredient

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


@dataclass
class ArbitraryItem:
    name: str
    aisle: str
    amount: float


NewItem = ArbitraryItem


def add_arbitrary_items(list_id: UUID,
                        arbitrary_items: list[ArbitraryItem],
                        conn: Connection) -> None:
    if not arbitrary_items:
        return

    conn.execute(
        insert(list_items), [
            {
                'list': list_id,
                'name': arbitrary_item.name,
                'aisle': arbitrary_item.aisle,
                'amount': arbitrary_item.amount
            } for arbitrary_item in arbitrary_items]
    )


def append_new_items(list_id: UUID, new_items: list[NewItem]) -> None:
    with engine.begin() as conn:
        add_arbitrary_items(list_id, new_items, conn)


class NoItemsToMakeAListError(Exception):
    pass


def add(date: datetime,
        recipe_scales: dict[UUID, float],
        included_ingredients: list[UUID],
        arbitrary_items: list[ArbitraryItem]) -> UUID:
    if not (recipe_scales or arbitrary_items):
        raise NoItemsToMakeAListError

    with engine.begin() as conn:
        # Create the base list item
        list_id = conn.execute(
            lists.insert().values(
                date=date
            ).returning(lists.c.id)
        ).mappings().one().id

        # Create the list items from chosen recipes
        if recipe_scales:
            add_recipe_items(list_id, recipe_scales, included_ingredients, conn)

        # Create the historical list arbitrary item information
        if arbitrary_items:
            add_arbitrary_items(list_id, arbitrary_items, conn)

    return list_id


@dataclass
class ShoppingListItem:
    id: UUID
    name: str
    amount: float


@dataclass
class ShoppingListAisle:
    name: str
    items: list[ShoppingListItem]


@dataclass
class IncludedRecipe:
    name: str
    scale: float


@dataclass
class ShoppingList:
    id: UUID
    date: datetime
    aisles: list[ShoppingListAisle]
    recipes_included: list[IncludedRecipe]


def for_shopping(id: UUID) -> ShoppingList:
    with engine.connect() as conn:
        shopping_items = conn.execute(
            select(list_items)
            .join(list_items, list_items.c.list == id)
            .where(lists.c.id == id)).mappings().all()
        shopping_list = conn.execute(
            select(lists).where(lists.c.id == id)
        ).mappings().one()

        aisles = {}

        for item in shopping_items:
            new_list_item = ShoppingListItem(item.id, item.name, item.amount)
            if item.aisle not in aisles:
                aisles[item.aisle] = ShoppingListAisle(item.aisle, [new_list_item])
            else:
                aisles[item.aisle].items += [new_list_item]

        included_recipes = []

        for included_recipe in conn.execute(
                list_recipes.select().where(list_recipes.c.list == id)).mappings().all():
            included_recipes += [IncludedRecipe(included_recipe.name, included_recipe.scale)]

    return ShoppingList(shopping_list.id,
                        shopping_list.date, list(aisles.values()), included_recipes)


def latest() -> list[List]:
    with engine.connect() as conn:
        latest = conn.execute(
            select(lists)
            .where(
                lists.c.date == func.current_date()
            )
            .order_by(lists.c.date)
        ).mappings().all()

    return [List(**latest_list) for latest_list in latest]


def update_date(id: UUID, new_date: datetime) -> None:
    with engine.connect() as conn:
        conn.execute(
            lists.update().values(
                date=new_date
            ).where(lists.c.id == id)
        )

        conn.commit()
