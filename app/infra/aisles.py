from sqlalchemy import select, union

from app.infra.db import engine, ingredients, quick_items


def all() -> list[str]:
    with engine.connect() as conn:
        query = union(
            select(ingredients.c.aisle),
            select(quick_items.c.aisle)
        )
        return list(conn.execute(
            query
        ).scalars())
