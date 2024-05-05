from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError

from app.infra.db import engine, quick_items


class QuickItemNotFoundError(Exception):
    pass


class DuplicateQuickItemError(Exception):
    pass


@dataclass
class QuickItem:
    id: UUID
    name: str
    aisle: str
    amount: float
    added_at: datetime


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


def delete(id: UUID) -> QuickItem:
    with engine.connect() as conn:
        deleted = conn.execute(
            quick_items.delete().where(quick_items.c.id == id)
            .returning(quick_items)
        ).mappings().first()

        conn.commit()

    if not deleted:
        raise QuickItemNotFoundError

    return QuickItem(**deleted)


def current() -> list[QuickItem]:
    with engine.connect() as conn:
        return [
            QuickItem(**item) for item in
            conn.execute(
                quick_items.select()
                .order_by(quick_items.c.added_at.desc())
            ).mappings().all()
        ]


def delete_all() -> None:
    with engine.connect() as conn:
        conn.execute(
            quick_items.delete()
        )

        conn.commit()
