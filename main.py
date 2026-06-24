import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from db.models import Base
from db.session import engine
from api.routes.chat import router as chat_router
from api.routes.jobs import router as jobs_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Creating database tables if they don't exist...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="AI Job Platform",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(jobs_router)


@app.get("/health")
async def health():
    return {"status": "ok", "message": "AI Job Platform API is running"}

app.mount("/app",StaticFiles(directory="frontend",html=True), name="frontend")
