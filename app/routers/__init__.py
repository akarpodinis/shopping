from typing import Annotated
from uuid import UUID

from fastapi import HTTPException, Path


def check_id(id: Annotated[str, Path()]) -> UUID:
    try:
        converted_id = UUID(id)
        if not converted_id.version == 4:
            raise ValueError
        return converted_id
    except ValueError:
        raise HTTPException(status_code=422, detail='id in path should be a v4 UUID')
