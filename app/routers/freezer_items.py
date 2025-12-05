from datetime import date, datetime
from html import escape
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.infra import freezer
from app.routers import check_id

router = APIRouter(prefix='/freezer-items')

templates = Jinja2Templates(directory='app/resources/templates/freezer_items')


# Ordering matters here.  I want the router to check /ingredients/new on GET before trying to
# figure out if the parameter is a UUID
@router.get('/new')
def new_form(request: Request, message: str = ''):
    return templates.TemplateResponse(
        request=request,
        name='new.html',
        context={
            'message': message,
            'guidelines': freezer.usda_freshness_guidelines()
        }
    )


@router.get('/list')
def list_page(request: Request, message: str = '') -> Response:
    items = freezer.actionable_list()

    # Probably want the freshness guidelines sent to the template here
    # too to, say, make a table for reference?
    return templates.TemplateResponse(
        request=request,
        name='list.html',
        context={
            'items': items,
            'message': message
        }
    )


@router.post('/{id}/update', dependencies=[Depends(check_id)])
def update_recipe(id: UUID,
                  name: Annotated[str, Form()],
                  amount: Annotated[int, Form()],
                  fda_item: Annotated[UUID, Form()],
                  stored_on: Annotated[datetime, Form()],
                  bag_id: Annotated[str | None, Form()] = None) -> Response:
    try:
        freezer.update(id, name, amount, fda_item, stored_on, bag_id)
        message = f'Success, updated freezer item {name}'
    except freezer.DuplicateBagIDError:
        message = f'Duplicate freezer bag ID called {bag_id}'

    return RedirectResponse(f'/freezer-items/list?message={escape(message)}', status_code=303)


@router.post('')
def new_freezer_item(
    submit_button: Annotated[str, Form()],
    name: Annotated[str, Form()],
    amount: Annotated[str, Form()],
    fda_item: Annotated[UUID, Form()],
    stored_on: Annotated[date, Form()],
    bag_id: Annotated[str | None, Form()] = None
) -> Response:
    try:
        freezer.add(name, amount, fda_item, stored_on, bag_id)
        message = f'Success, added freezer item {name}'
    except freezer.DuplicateBagIDError:
        message = f'Duplicate bag ID {bag_id}'
    
    destination = 'list' if 'done' in submit_button else 'new'

    return RedirectResponse(f'/freezer-items/{destination}?message={escape(message)}',
                            status_code=303)


@router.get('/{id}/edit', dependencies=[Depends(check_id)])
def edit_form(id: UUID, request: Request) -> Response:
    try:
        item = freezer.one(id)
        return templates.TemplateResponse(
            request=request,
            name='edit.html',
            context={
                'item': item,
                'guidelines': freezer.usda_freshness_guidelines()
            }
        )
    except freezer.FreezerItemNotFoundError:
        return Response(status_code=404)

@router.post('/{id}/delete')
def delete_recipe(id: UUID) -> Response:
    freezer.delete(id)
    
    return RedirectResponse(f'/freezer-items/list?message={escape('Freezer item deleted')}',
                            status_code=303)
