from html import escape
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.infra.quick import add, current, delete, DuplicateQuickItemError, QuickItemNotFoundError

router = APIRouter(prefix='/quick')

templates = Jinja2Templates(directory='app/resources/templates/lists')


@router.get('/{id}/delete')
def delete_quick_item(id: str, request: Request, response: Response) -> Response:
    try:
        converted_id = UUID(id)
        if not converted_id.version or not converted_id.version == 4:
            raise ValueError
    except ValueError:
        return Response(content='id in path should be a UUID', status_code=422)

    try:
        deleted = delete(id)
        message = f'Deleted quick item {deleted.name}'
    except QuickItemNotFoundError:
        message = 'Quick item already deleted'

    return RedirectResponse(f'/quick/list?message={escape(message)}', status_code=303)


@router.get('/list')
def quick_form(request: Request, message: str = '') -> Response:

    current_quick_items = current()

    return templates.TemplateResponse(
        request=request,
        name='quick.html',
        context={
            'message': message,
            'current': current_quick_items if current_quick_items else []
        }
    )


@router.post('/list')
def new_quick(quick_items: Annotated[list[str], Form()],
              quick_aisles: Annotated[list[str], Form()],
              quick_amounts: Annotated[list[str], Form()],
              request: Request) -> Response:
    resolved_items = []
    resolved_aisles = []
    resolved_amounts = []
    for index, item in enumerate(quick_items):
        if not item:
            continue

        resolved_items.append(item)
        resolved_aisles.append(quick_aisles[index])
        resolved_amounts.append(quick_amounts[index])

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
            'message': message,
            'current': current_quick_items if current_quick_items else []
        }
    )
