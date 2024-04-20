from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import index, ingredients, lists, quick, recipes

app = FastAPI()

app.mount('/styles', StaticFiles(directory='app/resources/styles/'), name='styles')
app.mount('/favicon', StaticFiles(directory='app/resources/images/favicon'), name='favicon')
app.mount('/fonts', StaticFiles(directory='app/resources/fonts/'), name='fonts')

app.include_router(index.router)
app.include_router(ingredients.router)
app.include_router(quick.router)
app.include_router(lists.router)
app.include_router(recipes.router)
