from typing import Any
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.infra.db import engine, quick_items


class DuplicateQuickItemError(Exception):
    pass


def add(items: list[str], aisles: list[str], amounts: list[int]) -> None:
    try:
        with engine.connect() as conn:
            conn.execute(
                quick_items.insert().values([
                    {
                        'name': item,
                        'aisle': aisles[index],
                        'amount': amounts[index]
                    } for index, item in enumerate(items)]
                )
            )

            conn.commit()
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise DuplicateQuickItemError
        else:
            raise


def delete(id: UUID) -> dict[str, Any]:
    with engine.connect() as conn:
        deleted = conn.execute(
            quick_items.delete().where(quick_items.c.id == id)
            .returning(quick_items)
        ).mappings().first()

        conn.commit()

    return dict(deleted)


def current() -> list[dict[str, Any]]:
    with engine.connect() as conn:
        return [
            dict(item) for item in
            conn.execute(
                quick_items.select()
                .order_by(quick_items.c.added_at.desc())
            ).mappings().all()
        ]
