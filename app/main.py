from fastapi import FastAPI

from app.routers import index, ingredients, lists, recipes

app = FastAPI()

app.include_router(index.router)
app.include_router(ingredients.router)
app.include_router(lists.router)
app.include_router(recipes.router)
