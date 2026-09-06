from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import get_settings
from app.db.bootstrap import seed_demo_data
from app.db.session import create_tables, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    await create_tables()
    await seed_demo_data()
    yield
    await engine.dispose()


settings = get_settings()
static_dir = Path(__file__).parent / "static"
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)
app.include_router(api_router, prefix="/api/v1")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
async def dashboard() -> FileResponse:
    return FileResponse(static_dir / "index.html")
