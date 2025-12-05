from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates

from app.infra import freezer

router = APIRouter(prefix='/freshness-table')

templates = Jinja2Templates(directory='app/resources/templates/freshness_table')


@router.get('')
def table(request: Request) -> Response:
    return templates.TemplateResponse(
        request=request,
        name='table.html',
        context={
            'guidelines': freezer.usda_freshness_guidelines()
        }
    )
