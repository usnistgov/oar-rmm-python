from fastapi import FastAPI
from app.routers import record

app = FastAPI()

app.include_router(record.router)