from html import escape
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.infra.ingredients import (
    DuplicateIngredientError, add, all, delete, edit_template_configuration,
    new_template_configuration, one, update
)
from app.routers.responses import UUIDJSONResponse

router = APIRouter(prefix='/ingredients')

templates = Jinja2Templates(directory='app/resources/templates/ingredients')


@router.get('')
def list_ingredients() -> Response:
    return UUIDJSONResponse(content=all())


# Ordering matters here.  I want the router to check /ingredients/new on GET before trying to
# figure out if the parameter is a UUID
@router.get('/new')
def new_form(request: Request):
    return templates.TemplateResponse(
        request=request,
        name='new.html',
        context=new_template_configuration()
    )


@router.get('/list')
def list_page(request: Request, message: str = '') -> Response:
    ingredients = all()

    return templates.TemplateResponse(
        request=request,
        name='list.html',
        context={
            'message': message,
            'ingredients': [(str(ingredient['id']),
                             ingredient['name'],
                             ingredient['aisle'],
                             '(stocked)' if ingredient['stocked'] else '')
                            for ingredient in ingredients]
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

    ingredient = one(id)
    return UUIDJSONResponse(content=ingredient if ingredient else None,
                            status_code=200 if ingredient else 404)


@router.post('')
def new_ingredient(submit_button: Annotated[str, Form()],
                   name: Annotated[str, Form()],
                   aisle: Annotated[str, Form()],
                   stocked: Annotated[bool, Form()] = False) -> Response:
    try:
        add(name, aisle, stocked)
        message = f'Success, added ingredient {name}'
    except DuplicateIngredientError:
        message = f'Duplicate ingredient called {name}'

    destination = 'list' if 'done' in submit_button else 'new'

    return RedirectResponse(f'/ingredients/{destination}?message={escape(message)}',
                            status_code=303)


# This should be a PATCH but HTML forms don't support that method.
# So, to work around it, allow POST to /ingredients/{id} :(
@router.post('/{id}')
def edit(id: str,
         name: Annotated[str, Form()] = None,
         aisle: Annotated[str, Form()] = None,
         stocked: Annotated[bool, Form()] = False) -> Response:
    try:
        update(UUID(id), stocked, name, aisle)
        message = f'Success, updated ingredient {name}'
    except DuplicateIngredientError:
        message = f'Duplicate ingredient called {name}'

    return RedirectResponse(f'/ingredients/list?message={escape(message)}', status_code=303)


@router.delete('/{id}')
def delete_one(id: str) -> Response:
    try:
        converted_id = UUID(id)
        if not converted_id.version or not converted_id.version == 4:
            raise ValueError
    except ValueError:
        return Response(content='id in path should be a UUID', status_code=422)

    delete(id)

    return RedirectResponse('/ingredients', status_code=303)


@router.get('/{id}/edit')
def edit_form(id: str, request: Request) -> Response:
    try:
        converted_id = UUID(id)
        if not converted_id.version or not converted_id.version == 4:
            raise ValueError
    except ValueError:
        return Response(content='id in path should be a UUID', status_code=422)

    return templates.TemplateResponse(
        request=request,
        name='edit.html',
        context=edit_template_configuration(id)
    )
