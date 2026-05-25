from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.garmin import router as garmin_router
from app.routes.metrics import router as metrics_router
from app.routes.plan import router as plan_router
from app.routes.workouts import router as workouts_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Marathon Coach", lifespan=lifespan)

# CORS: `web_origin` defaults to "*" for local dev; Railway env locks it to the Vercel URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.web_origin == "*" else [settings.web_origin],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

app.include_router(auth_router)
app.include_router(garmin_router)
app.include_router(admin_router)
app.include_router(chat_router)
app.include_router(plan_router)
app.include_router(workouts_router)
app.include_router(metrics_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
