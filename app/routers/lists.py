from datetime import datetime
from html import escape
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.infra import lists, quick, recipes
from app.routers import check_id

router = APIRouter(prefix='/lists')

templates = Jinja2Templates(directory='app/resources/templates/lists')


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
def new_form(request: Request, message: str = '') -> Response:
    current_summary = ', '.join(f'{item.amount}x {item.name}' for item in quick.current())

    return templates.TemplateResponse(
        request=request,
        name='new.html',
        context={
            'message': message,
            'quick_items': current_summary,
            'recipes': recipes.all()
        }
    )


@router.post('')
def add(date: Annotated[str, Form()],
        recipes: Annotated[list[str], Form()] = [],
        scales: Annotated[list[str], Form()] = [],
        include_quick_items: Annotated[bool, Form()] = False,
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

    if include_quick_items:
        for quick_item in quick.current():
            arbitrary_items.append(
                (quick_item.name, quick_item.aisle, quick_item.amount))

        quick.delete_all()

    try:
        added_list = lists.add(
            datetime.strptime(date, r'%Y-%m-%d'),
            dict(zip([UUID(recipe) for recipe in recipes], [float(scale) for scale in scales])),
            [UUID(ingredient) for ingredient in include_ingredients],
            arbitrary_items
        )
    except lists.NoItemsToMakeAListError:
        message = 'Pick some things to make a list'
        return RedirectResponse(f'/lists/new?message={escape(message)}', status_code=303)

    # Redirect to shopping list page
    return RedirectResponse(f'/lists/{added_list}/shopping', status_code=303)


@router.post('/confirm_stocked_and_arbitrary')
def confirm_stocked(request: Request,
                    date: Annotated[str, Form()],
                    included: Annotated[list[str], Form()] = [],
                    scales: Annotated[list[float], Form()] = [],
                    include_quick_items: Annotated[bool, Form()] = False,
                    message: str = '') -> Response:
    return templates.TemplateResponse(
        request=request,
        name='confirm_stocked_and_arbitrary.html',
        context={
            'message': message,
            'date': date,
            'recipes': included,
            'scales': scales,
            'include_quick_items': include_quick_items,
            'stocked_ingredients': recipes.stocked([UUID(recipe) for recipe in included])
        }
    )


@router.get('/{id}/shopping', dependencies=[Depends(check_id)])
def shopping(id: UUID, request: Request) -> Response:
    shopping_list = lists.for_shopping(id)
    return templates.TemplateResponse(
        request=request,
        name='shopping.html',
        context={
            'date': datetime.strftime(shopping_list.date, '%A, %B %-m, %Y'),
            'aisles': shopping_list.aisles,
            'recipes_included': ', '.join(
                f'{recipe.name} @ {recipe.scape}x' for recipe in shopping_list.recipes_included
            )
        }
    )


@router.get('/recent')
def recent(request: Request, count: int = 5) -> Response:
    return templates.TemplateResponse(
        request=request,
        name='inspiration.html',
        context={
            'recipes': lists.past_recipes(count)
        }
    )
