import random
from dataclasses import dataclass
from datetime import date
from functools import cache
from string import ascii_uppercase, digits
from uuid import UUID

from psycopg.errors import UniqueViolation
from sqlalchemy import RowMapping, extract, func, label, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import func as sql_funcs

from app.infra.db import engine, freezer_freshness, freezer_items

'''
Workflow
1. Show freezer items that are within two weeks of the end of their freshness on the
        New Shopping List page
2. Show freezer items that are past their freshness on the New Shopping List page
3. A page listing and allowing the deletion of freezer items
    List rows should show
        [1]. [Edit] [Delete] {amount} Freezer item (n weeks left)
4. A page allowing the adding of freezer items
    1. The freezer item name
    2. The amount
    3. The item type from the FDA list
    4. The date the item was put into the freezer, defaulting to today
    5. Optionally, a bag ID, if a bag needs to be re-inserted or the bag ID was previously
        misconfigured
'''


class DuplicateBagIDError(Exception):
    pass


@dataclass
class FreezerItem:
    id: UUID
    name: str
    amount: str
    freezer_bag_id: str
    freshness_id: UUID
    added_at: date


@dataclass
class FreezerItemWithTimeRemaining:
    id: UUID
    name: str
    over_stored: bool
    bag_id: str
    remaining: int
    
    @staticmethod
    def from_query(result: RowMapping) -> 'FreezerItemWithTimeRemaining':
        return FreezerItemWithTimeRemaining(
            result['id'],
            result['name'],
            result['over_stored'],
            result['freezer_bag_id'],
            max(result['remaining'], 0)
        )


def all() -> list[FreezerItem]:
    with engine.connect() as conn:
        return [FreezerItem(**item)
            for item in 
            # Add freshness_end and over_stored calculations to this query
                conn.execute(
                    select(freezer_items, freezer_freshness, func.now())
                    .select_from(
                        freezer_items.join(freezer_freshness,
                                           freezer_items.c.freshness_id == freezer_freshness.c.id)
                    )
                ).mappings().all()
        ]


class DuplicateFreezerItemError(Exception):
    pass


def update(
    id: UUID,
    name: str,
    amount: int,
    fda_guideline_id: UUID,
    stored_on: date,
    bag_id: str | None = None
) -> None:
    bag_id = ''.join(random.sample(
        ascii_uppercase + digits, 3
    )) if not bag_id else bag_id

    with engine.begin() as conn:
        try:
            conn.execute(
                insert(freezer_items).values(
                    id=id,
                    name=name,
                    freezer_bag_id=bag_id,
                    amount=amount,
                    added_at=stored_on,
                    freshness_id=fda_guideline_id
                ).on_conflict_do_update(
                    index_elements=[freezer_items.c.id],
                    set_={
                        freezer_items.c.name: name,
                        freezer_items.c.freezer_bag_id: bag_id,
                        freezer_items.c.amount: amount,
                        freezer_items.c.added_at: stored_on,
                        freezer_items.c.freshness_id: fda_guideline_id
                    }
                )
            )
        except IntegrityError as e:
            if isinstance(e.orig, UniqueViolation):
                raise DuplicateBagIDError
            else:
                raise



def actionable_list() -> list[FreezerItemWithTimeRemaining]:
    with engine.connect() as conn:
        return [FreezerItemWithTimeRemaining.from_query(item)
            for item in
                conn.execute(
                    select(
                        freezer_items,
                        label(
                            'remaining',
                            freezer_freshness.c.duration_days - 
                                extract('day', func.now() - freezer_items.c.added_at)
                        ),
                        label('over_stored',
                              freezer_items.c.added_at +
                              sql_funcs.make_interval(0, 0, 0, freezer_freshness.c.duration_days) <=
                              func.now()
                    )
                    ).select_from(
                        freezer_items.join(freezer_freshness,
                                           freezer_items.c.freshness_id == freezer_freshness.c.id)
                    )
                ).mappings().all()
        ]


def add(
    name: str,
    amount: str,
    fda_guideline_id: UUID,
    stored_on: date,
    bag_id: str | None = None
) -> UUID:
    bag_id = ''.join(random.sample(
        ascii_uppercase + digits, 3
    )) if not bag_id else bag_id

    try:
        with engine.begin() as conn:
            inserted = conn.execute(
                freezer_items.insert().values(
                    name=name,
                    freezer_bag_id=bag_id,
                    amount=amount,
                    added_at=stored_on,
                    freshness_id=fda_guideline_id
                ).returning(
                    freezer_items.c.id
                )
            ).mappings().one()
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise DuplicateBagIDError
        else:
            raise
        
    return inserted['id']
    

@dataclass
class USDAFreshnessGuideline:
    id: UUID
    name: str
    duration_days: int


# Cache this call, the database doesn't change and when it does I should make a migration and
# restart the service anyway.
@cache
def usda_freshness_guidelines() -> list[USDAFreshnessGuideline]:
    with engine.connect() as conn:
        return [USDAFreshnessGuideline(**item)
                for item in
                    conn.execute(
                        select(freezer_freshness)
                    ).mappings().all()
                ]


class FreezerItemNotFoundError(Exception):
    pass


def one(id: UUID) -> FreezerItem:
    with engine.connect() as conn:
        item = conn.execute(
            select(freezer_items).where(freezer_items.c.id == id)).mappings().one_or_none()

        if not item:
            raise FreezerItemNotFoundError

        return FreezerItem(**item)


def delete(id: UUID) -> None:
    with engine.begin() as conn:
        conn.execute(
            freezer_items.delete().where(freezer_items.c.id == id)
        )

def any_items_within_two_weeks_of_freshness_expiry() -> bool:
    with engine.connect() as conn:
        return True if conn.execute(
            select(freezer_items.c.id)
            .select_from(
                freezer_items.join(freezer_freshness,
                                    freezer_items.c.freshness_id == freezer_freshness.c.id)
            ).where(
                (freezer_items.c.added_at +
                 sql_funcs.make_interval(0, 0, 0, freezer_freshness.c.duration_days)) <=
                (func.now() - sql_funcs.make_interval(0, 0, 0, 14))
            ).limit(1)
        ).one_or_none() else False
