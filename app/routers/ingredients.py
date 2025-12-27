from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.infra import aisles, recipe_ingredients
from app.infra.ingredients import (
    DuplicateIngredientError, IngredientNotFoundError, add, all, delete, one, update
)
from app.routers import check_id

router = APIRouter(prefix='/ingredients')

templates = Jinja2Templates(directory='app/resources/templates/ingredients')


# Ordering matters here.  I want the router to check /ingredients/new on GET before trying to
# figure out if the parameter is a UUID
@router.get('/new')
def new_form(request: Request, message: str = ''):
    return templates.TemplateResponse(
        request=request,
        name='new.html',
        context={
            'aisle_names': aisles.all(),
            'message': message
        }
    )


@router.get('/list')
def list_page(request: Request, message: str = '') -> Response:
    ingredients = all()

    return templates.TemplateResponse(
        request=request,
        name='list.html',
        context={
            'message': message,
            'ingredients': ingredients
        }
    )


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

    return RedirectResponse(f'/ingredients/{destination}?message={quote(message)}',
                            status_code=303)


# This should be a PATCH but HTML forms don't support that method.
# So, to work around it, allow POST to /ingredients/{id} :(
@router.post('/{id}', dependencies=[Depends(check_id)])
def edit(id: UUID,
         name: Annotated[str | None, Form()] = None,
         aisle: Annotated[str | None, Form()] = None,
         stocked: Annotated[bool, Form()] = False) -> Response:
    try:
        update(id, stocked, name, aisle)
        message = f'Success, updated ingredient {name}'
    except DuplicateIngredientError:
        message = f'Duplicate ingredient called {name}'

    return RedirectResponse(f'/ingredients/list?message={quote(message)}', status_code=303)


@router.delete('/{id}', dependencies=[Depends(check_id)])
def delete_one(id: UUID) -> Response:
    delete(id)
    return RedirectResponse('/ingredients', status_code=303)


@router.get('/{id}/edit', dependencies=[Depends(check_id)])
def edit_form(id: UUID, request: Request) -> Response:
    try:
        ingredient = one(id)
        return templates.TemplateResponse(
            request=request,
            name='edit.html',
            context={
                'ingredient': ingredient,
                'aisle_names': aisles.all(),
                'recipes_using': recipe_ingredients.recipes_using(id)
            }
        )
    except IngredientNotFoundError:
        return Response(status_code=404)
