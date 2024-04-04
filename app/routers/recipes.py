from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.infra.ingredients import names_and_ids
from app.infra.recipes import (
    DuplicateRecipeError, RecipeDoesNotExistError, add, all, editable, one, update
)
from app.routers.responses import UUIDJSONResponse

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


@router.get('/list')
def list_page(request: Request, update_success: str = 'no change') -> Response:
    """
    update_success needs to be ternary.
    1. An update to a recipe was successful
    2. An update to a recipe was unsuccessful
    3. An update didn't happen at all
    """
    recipes = all()

    return templates.TemplateResponse(
        request=request,
        name='list.html',
        context={
            'recipes': recipes,
            'update_success': update_success
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

    try:
        recipe = one(id)
    except RecipeDoesNotExistError:
        return Response(status_code=404)
    else:
        return UUIDJSONResponse(content=recipe, status_code=200)


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
                'ingredients': recipe.ingredients,
                'ingredient_order': ingredient_order
            }
        )


@router.post('/{id}/update')
def update_recipe(id: str,
                  name: Annotated[str, Form()],
                  ingredient_order: Annotated[str, Form()],
                  amounts: Annotated[list[float], Form()] = None) -> Response:
    ingredient_amounts = []
    for index, ingredient in enumerate(ingredient_order.split(',')):
        ingredient_amounts += [(UUID(ingredient), amounts[index])]

    update(id, name, ingredient_amounts)

    return RedirectResponse('/recipes/list?update_success=yes', status_code=303)


@router.post('')
async def new_recipe(request: Request) -> Response:
    form_dict = await request.form()

    # Find and validate the recipe name
    try:
        name = form_dict['name']
        name = name.strip()
        if not name:
            return Response(content='Name is required', status_code=422)
    except KeyError:
        return Response(content='Name is required', status_code=422)

    # Find and validate the amounts for checked checkboxes
    # Magic '||' to get IDs.  The template has IDs set in the name with the form
    # "some-uuid||selected" for checkboxes and "some-uuid||amount" for amounts

    try:
        selected_ids = [
            UUID(key.split('||')[0]) for key in form_dict.keys() if 'on' in form_dict[key]
        ]
        amounts = []
        for selected_id in selected_ids:
            try:
                amount = int(form_dict[f'{selected_id}||amount'])
                amounts.append((selected_id, amount))
            except ValueError as e:
                return Response(content=f'Amount {e} should be an integer', status_code=422)

        inserted = add(name, amounts)
    except DuplicateRecipeError:
        return Response(content=f'Duplicate recipe with name {name}', status_code=409)

    return RedirectResponse(f'/recipes/{inserted}', status_code=303)
