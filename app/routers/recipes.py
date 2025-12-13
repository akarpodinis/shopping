from typing import Annotated
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.infra.ingredients import names_and_ids
from app.infra.recipes import (
    DuplicateRecipeError, IngredientAmounts, RecipeDoesNotExistError, add, all, all_ingredients,
    delete, editable, send_to_quick_list, update
)
from app.routers import check_id

router = APIRouter(prefix='/recipes')

templates = Jinja2Templates(directory='app/resources/templates/recipes')


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


@router.get('/{id}/edit', dependencies=[Depends(check_id)])
def edit(id: UUID, request: Request) -> Response:
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


@router.post('/{id}/update', dependencies=[Depends(check_id)])
def update_recipe(id: UUID,
                  name: Annotated[str, Form()],
                  servings: Annotated[int, Form()],
                  ingredient_order: Annotated[str, Form()],
                  is_routine: Annotated[bool, Form()] = False,
                  notes: Annotated[str, Form()] = '',
                  amounts: Annotated[list[float], Form()] = []) -> Response:
    ingredient_amounts: list[IngredientAmounts] = []
    for index, ingredient in enumerate(ingredient_order.split(',')):
        ingredient_amounts += [(UUID(ingredient), amounts[index])]

    try:
        update(id, name, is_routine, servings, ingredient_amounts, notes)
        message = f'Success, updated recipe {name}'
    except DuplicateRecipeError:
        message = f'Duplicate recipe called {name}'

    return RedirectResponse(f'/recipes/list?message={quote(message)}', status_code=303)


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
        amounts: list[IngredientAmounts] = []
        for selected_id in selected_ids:
            try:
                form_amount = form_dict[f'{selected_id}||amount']
                if not isinstance(form_amount, str):
                    raise TypeError('Strings only when POSTing a new recipe')
                amount = float(form_amount)
                amounts.append((selected_id, amount))
            except ValueError as e:
                return Response(content=f'Amount {e} should be an integer', status_code=422)

        add(name, is_routine, servings, amounts)
        message = f'Success, added recipe {name}'
    except DuplicateRecipeError:
        message = f'Duplicate recipe called {name}'

    return RedirectResponse(f'/recipes/list?message={quote(message)}', status_code=303)


@router.post('/{id}/delete')
def delete_recipe(id: UUID) -> Response:
    
    delete(id)
    
    return RedirectResponse(f'/recipes/list?message={quote('Success, recipe deleted')}',
                            status_code=303)


@router.post('/{id}/send-to-quick-list')
def confirm_stocked_when_sending_to_quick_list(
    id: UUID,
    scale: Annotated[float, Form()],
    include_ingredients: Annotated[list[UUID], Form()] = []
) -> Response:
    send_to_quick_list(id, include_ingredients, scale)
    return RedirectResponse(f'/recipes/list?message={quote('Success, sent to quick list')}',
                            status_code=303)


@router.get('/{id}/prepare-to-send-to-quick-list')
def send_check_stock_form(id: UUID, request: Request) -> Response:
    return templates.TemplateResponse(
            request=request,
            name='check-stocked.html',
            context={
                'id': id,
                'ingredients': all_ingredients(id)
            }
        )
