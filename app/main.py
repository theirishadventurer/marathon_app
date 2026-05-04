from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routes.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Marathon Coach", lifespan=lifespan)
app.include_router(auth_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
