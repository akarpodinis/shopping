from fastapi import FastAPI

from app.routers import index, ingredients, recipes

app = FastAPI()

app.include_router(index.router)
app.include_router(ingredients.router)
app.include_router(recipes.router)
