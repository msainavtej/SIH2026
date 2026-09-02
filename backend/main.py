from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from backend.api import events, alerts, cameras, analytics, storage
from backend.camera_manager import camera_manager
from backend.storage_manager import storage_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    camera_manager.load_cameras()
    camera_manager.start_all()
    storage_manager.start_governor()
    yield
    camera_manager.stop_all()
    storage_manager.stop()

app = FastAPI(
    title="Border AI Platform API",
    description="API for SIH PS187 Border Surveillance Platform",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events.router, prefix="/api", tags=["events"])
app.include_router(cameras.router, prefix="/api", tags=["cameras"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(storage.router, prefix="/api", tags=["storage"])
app.include_router(alerts.router, tags=["alerts"])

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "0.1.0"}
