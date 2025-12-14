from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import quote
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.infra import aisles, lists, quick, recipes
from app.infra.db import engine
from app.infra.lists import ArbitraryItem, NewItem, delete, move_inverse_to_quick_list
from app.routers import check_id

router = APIRouter(prefix='/lists')

templates = Jinja2Templates(directory='app/resources/templates/lists')


@router.get('/list')
def list_lists(request: Request, message: str = '') -> Response:
    all_lists = lists.all()

    return templates.TemplateResponse(
        request=request,
        name='list.html',
        context={
            'all_lists': all_lists,
            'message': message
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
            'today': datetime.strftime(datetime.now(ZoneInfo('America/New_York')), r'%Y-%m-%d'),
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
    arbitrary_items: list[ArbitraryItem] = []

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
        return RedirectResponse(f'/lists/new?message={quote(message)}', status_code=303)

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
            'stocked_ingredients': recipes.stocked(included),
            'aisle_names': aisles.all()
        }
    )


@router.get('/{id}/update', dependencies=[Depends(check_id)])
def add_to_list(request: Request, id: UUID) -> Response:
    shopping_list = lists.for_shopping(id)
    return templates.TemplateResponse(
        request=request,
        name='add_some_more_items.html',
        context={
            'aisle_names': aisles.all(),
            'date': datetime.strftime(shopping_list.date, '%Y-%m-%d'),
            'list': shopping_list,
        }
    )


@router.get('/{id}/shopping', dependencies=[Depends(check_id)])
def shopping(id: UUID, request: Request, message: str = '') -> Response:
    shopping_list = lists.for_shopping(id)
    return templates.TemplateResponse(
        request=request,
        name='shopping.html',
        context={
            'message': message,
            'formatted_date': datetime.strftime(shopping_list.date, r'%A, %B %-d, %Y'),
            'raw_date': shopping_list.date.date(),
            'list': shopping_list,
            'allow_adding_items': shopping_list.date.day >= datetime.now(UTC).day,
            'allow_deleting_list': shopping_list.date.day < datetime.now(UTC).day,
            'recipes_included': ', '.join(
                f'{recipe.name} @ {recipe.scale}x' for recipe in shopping_list.recipes_included
            )
        }
    )


@router.post('/{id}/add-more-items', dependencies=[Depends(check_id)])
def add_more_items(request: Request,
                   id: UUID,
                   date: Annotated[str, Form()],
                   names: Annotated[list[str], Form()] = [],
                   aisles: Annotated[list[str], Form()] = [],
                   amounts: Annotated[list[str], Form()] = []) -> Response:
    new_items: list[NewItem] = []
    for index, name in enumerate(names):
        # Ignore the whole arbitrary item row if the name is blank
        if not name:
            continue
        new_items.append(NewItem(
            name,
            aisles[index],
            float(amounts[index])
        ))

    lists.append_new_items(id, new_items)
    
    lists.update_date(id, datetime.strptime(date, r'%Y-%m-%d'))

    # Redirect to shopping list page
    message = 'Successfully updated the list'
    return RedirectResponse(f'/lists/{id}/shopping?message={quote(message)}', status_code=303)


@router.post('/{id}/send-to-quick-list', dependencies=[Depends(check_id)])
async def return_to_quick_list(id: UUID, request: Request) -> Response:
    # Paired identical UUIDs from the form
    gathered_items: list[UUID] = []
    for pair in await request.form():
        gathered_items.append(UUID(pair))
    
    if not gathered_items:
        return RedirectResponse(
            f'/lists/{id}/shopping?message={quote('Nothing to move')}', status_code=303
        )

    
    # Delete from the shopping list the items not in the incoming list, returning the deleted names,
    # aisles and amounts to quick items, then send items to the quick list
    with engine.begin() as conn:
        move_inverse_to_quick_list(id, gathered_items, conn)
    
    # Redirect to the current list page to refresh the data.
    return RedirectResponse(
        f'/lists/{id}/shopping?message={quote('Done moving to the quick list')}', status_code=303
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


@router.post('/{id}/delete')
def delete_list(id: UUID) -> Response:
    delete(id)
    return RedirectResponse(
        f'/lists/list?message={quote('Success, deleted the list')}', status_code=303
    )
