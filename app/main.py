from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.database import init_db
from app.routes_auth import router as auth_router
from app.routes_tasks import router as tasks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Tasks API", lifespan=lifespan)

app.include_router(auth_router)
app.include_router(tasks_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}