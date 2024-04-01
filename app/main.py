from fastapi import FastAPI

from app.routers import ingredients

app = FastAPI()

app.include_router(ingredients.router)
