from html import escape
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.infra.ingredients import names_and_ids
from app.infra.recipes import (
    DuplicateRecipeError, RecipeDoesNotExistError, add, all, editable, update
)
from app.routers.responses import UUIDJSONResponse

router = APIRouter(prefix='/recipes')

templates = Jinja2Templates(directory='app/resources/templates/recipes')


@router.get('')
def list_ingredients() -> Response:
    return UUIDJSONResponse(content=all())


# Ordering matters here.  I want the router to check /recipes/new on GET before trying to
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


@router.get('/list')
def list_page(request: Request, message: str = '') -> Response:
    recipes = all()

    return templates.TemplateResponse(
        request=request,
        name='list.html',
        context={
            'recipes': recipes,
            'message': message
        }
    )


@router.get('/{id}/edit')
def edit(id: str, request: Request) -> Response:
    try:
        converted_id = UUID(id)
        if not converted_id.version or not converted_id.version == 4:
            raise ValueError
    except ValueError:
        return Response(content='id in path should be a UUID', status_code=422)

    try:
        recipe = editable(id)
    except RecipeDoesNotExistError:
        return Response(status_code=404)
    else:
        ingredient_order = ','.join([str(ingredient.id) for ingredient in recipe.ingredients])

        return templates.TemplateResponse(
            request=request,
            name='edit.html',
            context={
                'id': id,
                'name': recipe.name,
                'already_routine': 'checked' if recipe.routine else '',
                'servings': recipe.servings,
                'ingredients': recipe.ingredients,
                'ingredient_order': ingredient_order,
                'notes': recipe.notes
            }
        )


@router.post('/{id}/update')
def update_recipe(id: str,
                  name: Annotated[str, Form()],
                  servings: Annotated[int, Form()],
                  ingredient_order: Annotated[str, Form()],
                  is_routine: Annotated[bool, Form()] = False,
                  notes: Annotated[str, Form()] = None,
                  amounts: Annotated[list[float], Form()] = None) -> Response:
    ingredient_amounts = []
    for index, ingredient in enumerate(ingredient_order.split(',')):
        ingredient_amounts += [(UUID(ingredient), amounts[index])]

    try:
        update(id, name, is_routine, servings, ingredient_amounts, notes)
        message = f'Success, updated recipe {name}'
    except DuplicateRecipeError:
        message = f'Duplicate recipe called {name}'

    return RedirectResponse(f'/recipes/list?message={escape(message)}', status_code=303)


@router.post('')
async def new_recipe(name: Annotated[str, Form()], servings: Annotated[int, Form()],
                     request: Request, is_routine: Annotated[bool, Form()] = False) -> Response:
    form_dict = await request.form()

    # Find and validate the amounts for checked checkboxes
    # Magic '||' to get IDs.  The template has IDs set in the name with the form
    # "some-uuid||selected" for checkboxes and "some-uuid||amount" for amounts

    try:
        selected_ids = [
            UUID(key.split('||')[0]) for key in form_dict.keys() if 'selected' in key
        ]
        amounts = []
        for selected_id in selected_ids:
            try:
                amount = int(form_dict[f'{selected_id}||amount'])
                amounts.append((selected_id, amount))
            except ValueError as e:
                return Response(content=f'Amount {e} should be an integer', status_code=422)

        add(name, is_routine, servings, amounts)
        message = f'Success, added recipe {name}'
    except DuplicateRecipeError:
        message = f'Duplicate recipe called {name}'

    return RedirectResponse(f'/recipes/list?message={escape(message)}', status_code=303)
