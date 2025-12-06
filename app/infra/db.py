import os
import re

import sqlalchemy as sa
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKeyConstraint, Integer, String, Table, Text,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import CITEXT, UUID

database_url = re.sub('postgres(?:ql)?:', 'postgresql+psycopg:', os.environ['DATABASE_URL'])

engine = sa.create_engine(database_url, pool_pre_ping=True)

metadata = sa.MetaData()
metadata.bind = engine

new_uuid = sa.text('uuid_generate_v4()')


ingredients = Table(
    'ingredients',
    metadata,
    Column('id', UUID(as_uuid=True), server_default=new_uuid, primary_key=True),
    Column('name', CITEXT, unique=True, nullable=False),
    Column('aisle', String, nullable=False),
    Column('stocked', Boolean, nullable=False, default=False),
    UniqueConstraint('name')
)

recipes = Table(
    'recipes',
    metadata,
    Column('id', UUID(as_uuid=True), server_default=new_uuid, primary_key=True),
    Column('name', CITEXT, unique=True, nullable=False),
    Column('servings', Integer, nullable=False),
    Column('routine', Boolean, nullable=False, default=False),
    UniqueConstraint('name')
)

recipe_notes = Table(
    'recipe_notes',
    metadata,
    Column('recipe', UUID(as_uuid=True), nullable=False),
    Column('notes', Text),
    UniqueConstraint('recipe', name='recipe_notes_recipe_key'),
    ForeignKeyConstraint(
        ['recipe'],
        ['recipes.id'],
        'recipe_notes_recipe_fkey',
        ondelete='CASCADE'
    )
)

ingredients_recipes = Table(
    'ingredients_recipes',
    metadata,
    Column('recipe', UUID(as_uuid=True), nullable=False),
    Column('ingredient', UUID(as_uuid=True), nullable=False),
    Column('amount', Float, default=0),
    UniqueConstraint('recipe', 'ingredient', name='recipe_ingredient_key')
)

lists = Table(
    'lists',
    metadata,
    Column('id', UUID(as_uuid=True), server_default=new_uuid, primary_key=True),
    Column('date', DateTime(timezone=True), nullable=True)
)

list_recipes = Table(
    'lists_recipes',
    metadata,
    Column('list', UUID(as_uuid=True), nullable=False),
    Column('name', String, nullable=False),
    Column('scale', Float, nullable=False, default=1.0)
)

list_items = Table(
    'list_items',
    metadata,
    Column('id', UUID(as_uuid=True), server_default=new_uuid, primary_key=True),
    Column('list', UUID(as_uuid=True), nullable=False),
    Column('name', String, nullable=False),
    Column('aisle', String, nullable=False),
    Column('amount', Float, nullable=False, default=0)
)

quick_items = Table(
    'quick_items',
    metadata,
    Column('id', UUID(as_uuid=True), server_default=new_uuid, primary_key=True),
    Column('name', CITEXT, nullable=False),
    Column('aisle', String, nullable=False),
    Column('amount', Float, nullable=False, default=0),
    Column('added_at', DateTime, nullable=True),
    UniqueConstraint('name', name='quick_items_name_key')
)

freezer_items = Table(
    'freezer_items',
    metadata,
    Column('id', UUID(as_uuid=True), server_default=new_uuid, primary_key=True),
    Column('name', CITEXT, nullable=False),
    Column('freezer_bag_id', CITEXT, nullable=False, unique=True),
    Column('amount', Float, nullable=False, default=0),
    Column('added_at', DateTime, nullable=True),
    Column('freshness_id', UUID(as_uuid=True), nullable=False),
    ForeignKeyConstraint(
        ['freshness_id'],
        ['freezer_freshness.id'],
        'freezer_items_id_freezer_freshness_id_fkey'
    )
)

freezer_freshness = Table(
    'freezer_freshness',
    metadata,
    Column('id', UUID(as_uuid=True), server_default=new_uuid, primary_key=True),
    Column('name', CITEXT, nullable=False),
    Column('duration_days', Integer, nullable=False),
)

"""
Freezer item plan
* Add items in the freezer, choose expected CDC freshness duration based on item type
* Server gives a simple alphanumeric bag ID to write on the storage bag
* Delete freezer items when they're removed
* Show food that is reaching the end of its quality about two weeks before the stored freshness when making a list
"""
