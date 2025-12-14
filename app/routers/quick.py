from datetime import datetime
from typing import Annotated
from urllib.parse import quote
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.infra import aisles
from app.infra.db import engine
from app.infra.lists import ArbitraryItem
from app.infra.lists import add as add_list
from app.infra.quick import (
    DuplicateQuickItemError, QuickItemNotFoundError, add, current, delete, delete_some
)
from app.routers import check_id

router = APIRouter(prefix='/quick')

templates = Jinja2Templates(directory='app/resources/templates/quick')


@router.get('/confirm-turn-into-a-list')
def confirm_turn_into_list(request: Request) -> Response:
    return templates.TemplateResponse(
        request=request,
        name='check-stocked.html',
        context={
            'today': datetime.strftime(datetime.now(ZoneInfo('America/New_York')), r'%Y-%m-%d'),
            'items': current()
        }
    )


@router.post('/turn-into-a-list')
def turn_into_a_list(date: Annotated[str, Form()],
                     include_items: Annotated[list[UUID], Form()] = []) -> Response:
    if not include_items:
        return RedirectResponse(
            f'/quick/list?message={quote('No items selected')}',
            status_code=303
        )

    current_quick_items = current()
    
    with engine.begin() as conn:
        list_id = add_list(
            datetime.strptime(date, r'%Y-%m-%d'),
            {},
            [],
            [ArbitraryItem(item.name, item.aisle, item.amount)
             for item in current_quick_items if item.id in include_items],
            conn
        )
        
        delete_some(include_items, conn)
    
    return RedirectResponse(
        f'/lists/{list_id}/shopping?message={quote('Success, here\'s your list')}',
        status_code=303
    )



@router.get('/{id}/delete', dependencies=[Depends(check_id)])
def delete_quick_item(id: UUID) -> Response:
    try:
        deleted = delete(id)
        message = f'Deleted quick item {deleted.name}'
    except QuickItemNotFoundError:
        message = 'Quick item already deleted'

    return RedirectResponse(f'/quick/list?message={quote(message)}', status_code=303)


@router.get('/list')
def quick_form(request: Request, message: str = '') -> Response:

    current_quick_items = current()

    return templates.TemplateResponse(
        request=request,
        name='quick.html',
        context={
            'aisle_names': aisles.all(),
            'message': message,
            'current': current_quick_items if current_quick_items else []
        }
    )


@router.post('/list')
def new_quick(quick_items: Annotated[list[str], Form()],
              quick_aisles: Annotated[list[str], Form()],
              quick_amounts: Annotated[list[str], Form()],
              request: Request) -> Response:
    resolved_items: list[str] = []
    resolved_aisles: list[str] = []
    resolved_amounts: list[float] = []
    for index, item in enumerate(quick_items):
        if not item:
            continue

        resolved_items.append(item)
        resolved_aisles.append(quick_aisles[index])
        resolved_amounts.append(float(quick_amounts[index]))

    try:
        add(resolved_items, resolved_aisles, resolved_amounts)
        message = 'Success, added quick items'
    except DuplicateQuickItemError:
        message = 'Duplicate quick item in your list'

    current_quick_items = current()

    return templates.TemplateResponse(
        request=request,
        name='quick.html',
        context={
            'aisle_names': aisles.all(),
            'message': message,
            'current': current_quick_items if current_quick_items else []
        }
    )
