from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.core.config import get_settings
from app.core.database import Base, SessionLocal, engine
from app.services.seed import seed_reference_data


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_reference_data(db)
    yield


settings = get_settings()
app = FastAPI(title="Matrix One Market API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:7890",
        "http://127.0.0.1:7890",
        settings.public_web_url.rstrip("/"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
