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


@app.middleware("http")
async def cache_public_reads(request, call_next):
    response = await call_next(request)
    cacheable_paths = (
        "/api/v1/country-opportunities",
        "/api/v1/catalog/hs",
        "/api/v1/products/search",
    )
    if request.method == "GET" and request.url.path.startswith(cacheable_paths):
        # Public market data changes only after an import/analysis.  Let the
        # browser reuse a recent response when navigating between pages.
        response.headers["Cache-Control"] = "public, max-age=60, stale-while-revalidate=300"
    return response


app.include_router(router)
