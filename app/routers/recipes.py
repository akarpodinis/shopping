from uuid import UUID
from fastapi import APIRouter, Request, Response
from fastapi.templating import Jinja2Templates

from app.routers.responses import UUIDJSONResponse
from app.infra.ingredients import names_and_ids
from app.infra.recipes import all, one

router = APIRouter(prefix='/recipes')

templates = Jinja2Templates(directory='app/templates/recipes')


@router.get('')
def list_ingredients() -> Response:
    return UUIDJSONResponse(content=all())


# Ordering matters here.  I want the router to check /ingredients/new on GET before trying to
# figure out if the parameter is a UUID
@router.get('/new')
def new_form(request: Request):
    names, ids = names_and_ids()
    return templates.TemplateResponse(
        request=request,
        name='new.html',
        context={
            'names': names,
            'ids': ids
        }
    )


@router.get('/{id}')
def get_one(id: str) -> Response:
    try:
        converted_id = UUID(id)
        if not converted_id.version or not converted_id.version == 4:
            raise ValueError
    except ValueError:
        return Response(content='id in path should be a UUID', status_code=422)

    recipe = one(id)
    return UUIDJSONResponse(content=recipe if recipe else None,
                            status_code=200 if recipe else 404)
