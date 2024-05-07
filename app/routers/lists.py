from datetime import datetime
from html import escape
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.infra import lists, quick, recipes
from app.infra.lists import ArbitraryItem
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
        recipes: Annotated[list[UUID], Form()] = [],
        scales: Annotated[list[float], Form()] = [],
        include_quick_items: Annotated[bool, Form()] = False,
        include_ingredients: Annotated[list[UUID], Form()] = [],
        arbitrary_names: Annotated[list[str], Form()] = [],
        arbitrary_aisles: Annotated[list[str], Form()] = [],
        arbitrary_amounts: Annotated[list[str], Form()] = []) -> Response:

    # Filter empty arbitrary rows
    arbitrary_items = []

    for index, name in enumerate(arbitrary_names):
        # Ignore the whole arbitrary item row if the name is blank
        if not name:
            continue
        arbitrary_items.append(ArbitraryItem(
            name,
            arbitrary_aisles[index],
            float(arbitrary_amounts[index])
        ))

    if include_quick_items:
        for quick_item in quick.current():
            arbitrary_items.append(
                ArbitraryItem(quick_item.name, quick_item.aisle, quick_item.amount))

    try:
        added_list = lists.add(
            datetime.strptime(date, r'%Y-%m-%d'),
            dict(zip([recipe for recipe in recipes], [scale for scale in scales])),
            include_ingredients,
            arbitrary_items
        )
        # This isn't the right way to do this, the request scope should manage when these items
        # are deleted with a commit and a rollback and then I can remove the following check.
        if include_quick_items:
            quick.delete_all()
    except lists.NoItemsToMakeAListError:
        message = 'Pick some things to make a list'
        return RedirectResponse(f'/lists/new?message={escape(message)}', status_code=303)

    # Redirect to shopping list page
    return RedirectResponse(f'/lists/{added_list}/shopping', status_code=303)


@router.post('/confirm_stocked_and_arbitrary')
def confirm_stocked(request: Request,
                    date: Annotated[str, Form()],
                    available: Annotated[list[UUID], Form()],
                    included: Annotated[list[UUID], Form()] = [],
                    scales: Annotated[list[float], Form()] = [],
                    include_quick_items: Annotated[bool, Form()] = False,
                    message: str = '') -> Response:
    chosen_indexes = [available.index(i) for i in included]
    return templates.TemplateResponse(
        request=request,
        name='confirm_stocked_and_arbitrary.html',
        context={
            'message': message,
            'date': date,
            'recipes': included,
            'scales': [scales[index] for index in chosen_indexes],
            'include_quick_items': include_quick_items,
            'stocked_ingredients': recipes.stocked(included)
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
                f'{recipe.name} @ {recipe.scale}x' for recipe in shopping_list.recipes_included
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
