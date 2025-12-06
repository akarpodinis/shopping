from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates

from app.infra.freezer import any_items_within_two_weeks_of_freshness_expiry
from app.infra.lists import latest

router = APIRouter(prefix='')

templates = Jinja2Templates(directory='app/resources/templates/index')


@router.get('/')
def index(request: Request) -> Response:
    recent_lists = latest()
    return templates.TemplateResponse(
        request=request,
        name='index.html',
        context={
            'recent_lists': recent_lists,
            'some_close_to_past_freshness': any_items_within_two_weeks_of_freshness_expiry()
        }
    )
