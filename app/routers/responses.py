import json
from typing import Any

from fastapi import Response

from app.encoding import UUIDEncoder


class UUIDJSONResponse(Response):
    media_type = 'application/json'

    def render(self, content: Any) -> bytes:
        return json.dumps(content, cls=UUIDEncoder).encode()
