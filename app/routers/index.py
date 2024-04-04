from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix='')

templates = Jinja2Templates(directory='app/resources/templates/index')


@router.get('/')
def index(request: Request) -> Response:
    return templates.TemplateResponse(request=request, name='index.html')
