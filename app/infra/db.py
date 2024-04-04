import os
import re

import sqlalchemy as sa
from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, String, Table, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import CITEXT, UUID

database_url = re.sub('postgres(?:ql)?:', 'postgresql+psycopg:', os.environ['DATABASE_URL'])

engine = sa.create_engine(database_url)

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
    UniqueConstraint('name')
)

recipe_notes = Table(
    'recipe_notes',
    metadata,
    Column('recipe', UUID(as_uuid=True), nullable=False),
    Column('notes', Text),
    UniqueConstraint('recipe', name='recipe_notes_recipe_key')
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
    Column('date', DateTime, nullable=True)
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
    Column('list', UUID(as_uuid=True), nullable=False),
    Column('name', String, nullable=False),
    Column('aisle', String, nullable=False),
    Column('amount', Float, nullable=False, default=0)
)
