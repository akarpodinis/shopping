import os
import re

import sqlalchemy as sa
from sqlalchemy import Boolean, Column, Float, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

database_url = re.sub('postgres(?:ql)?:', 'postgresql+psycopg:', os.environ['DATABASE_URL'])

engine = sa.create_engine(database_url)

metadata = sa.MetaData()
metadata.bind = engine

new_uuid = sa.text('uuid_generate_v4()')


ingredients = Table(
    'ingredients',
    metadata,
    Column('id', UUID(as_uuid=True), server_default=new_uuid, primary_key=True),
    Column('name', String, unique=True, nullable=False),
    Column('aisle', String, nullable=False),
    Column('stocked', Boolean, default=False),
    UniqueConstraint('name')
)

recipes = Table(
    'recipes',
    metadata,
    Column('id', UUID(as_uuid=True), server_default=new_uuid, primary_key=True),
    Column('name', String, unique=True, nullable=False),
    UniqueConstraint('name')
)

ingredients_recipes = Table(
    'ingredients_recipes',
    metadata,
    Column('recipe', UUID(as_uuid=True), nullable=False),
    Column('ingredient', UUID(as_uuid=True), nullable=False),
    Column('amount', Float, default=0),
    UniqueConstraint('recipe', 'ingredient', name='recipe_ingredient_key')
)
