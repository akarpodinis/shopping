from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.infra import lists, recipes

router = APIRouter(prefix='/lists')

templates = Jinja2Templates(directory='app/templates/lists')


@router.get('/list')
def list_lists(request: Request) -> Response:
    all_lists = lists.all()

    return templates.TemplateResponse(
        request=request,
        name='list.html',
        context={
            'all_lists': all_lists
        }
    )


# Ordering matters here.  I want the router to check /ingredients/new on GET before trying to
# figure out if the parameter is a UUID
@router.get('/new')
def new_form(request: Request) -> Response:
    names = []
    ids = []
    for recipe in recipes.all():
        names.append(recipe['name'])
        ids.append(recipe['id'])

    return templates.TemplateResponse(
        request=request,
        name='new.html',
        context={
            'recipe_names': names,
            'recipe_ids': ids
        }
    )


@router.post('')
def add(date: Annotated[str, Form()],
        recipes: Annotated[list[str], Form()],
        scales: Annotated[list[str], Form()],
        include_ingredients: Annotated[list[str], Form()] = [],
        arbitrary_names: Annotated[list[str], Form()] = [],
        arbitrary_aisles: Annotated[list[str], Form()] = [],
        arbitrary_amounts: Annotated[list[str], Form()] = []) -> Response:

    # Filter empty arbitrary rows
    arbitrary_items = []

    for index, name in enumerate(arbitrary_names):
        # Ignore the whole arbitrary item row if the name is blank
        if not name:
            continue
        arbitrary_items.append((name, arbitrary_aisles[index], int(arbitrary_amounts[index])))

    added_list = lists.add(
        datetime.strptime(date, r'%Y-%m-%d'),
        dict(zip([UUID(recipe) for recipe in recipes], [float(scale) for scale in scales])),
        [UUID(ingredient) for ingredient in include_ingredients],
        arbitrary_items
    )

    # Redirect to shopping list page
    return RedirectResponse(f'/lists/{added_list}/shopping', status_code=303)


@router.post('/confirm_stocked_and_arbitrary')
def confirm_stocked(date: Annotated[str, Form()], included: Annotated[list[str], Form()],
                    scales: Annotated[list[float], Form()], request: Request) -> Response:
    ids = []
    names = []
    for id, name in recipes.stocked([UUID(recipe) for recipe in included]):
        ids.append(id)
        names.append(name)
    return templates.TemplateResponse(
        request=request,
        name='confirm_stocked_and_arbitrary.html',
        context={
            'date': date,
            'recipes': included,
            'scales': scales,
            'ids': ids,
            'names': names
        }
    )


@router.get('/{id}/shopping')
def shopping(id: str, request: Request) -> Response:
    shopping_list = lists.for_shopping(UUID(id))
    return templates.TemplateResponse(
        request=request,
        name='shopping.html',
        context={
            'date': datetime.strftime(shopping_list.date, '%A, %B %-m, %Y'),
            'aisles': shopping_list.aisles
        }
    )


@router.get('/recent')
def recent(request: Request, count: int = 5) -> Response:
    historical_lists = lists.past_recipes(count)

    return templates.TemplateResponse(
        request=request,
        name='inspiration.html',
        context={
            'recipe_names': [historical_list['name'] for historical_list in historical_lists]
        }
    )
