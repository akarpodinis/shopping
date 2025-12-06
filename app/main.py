from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import freezer_items, freshness_table, index, ingredients, lists, quick, recipes

app = FastAPI()

app.mount('/styles', StaticFiles(directory='app/resources/fonts-and-styles/styles/'), name='styles')
app.mount('/scripts', StaticFiles(directory='app/resources/scripts'), name='scripts')
app.mount('/favicon', StaticFiles(directory='app/resources/images/favicon'), name='favicon')
app.mount('/fonts', StaticFiles(directory='app/resources/fonts-and-styles/fonts/'), name='fonts')

app.include_router(index.router)
app.include_router(ingredients.router)
app.include_router(quick.router)
app.include_router(lists.router)
app.include_router(recipes.router)
app.include_router(freezer_items.router)
app.include_router(freshness_table.router)
