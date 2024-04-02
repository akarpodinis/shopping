from fastapi import APIRouter, Response
from starlette.responses import FileResponse

router = APIRouter(prefix='')


@router.get('/')
def index() -> Response:
    return FileResponse('app/templates/index/index.html')
