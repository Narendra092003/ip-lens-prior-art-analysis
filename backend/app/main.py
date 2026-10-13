"""FastAPI application entry point."""

from fastapi import FastAPI

from backend.app.api import router

app = FastAPI(
    title="IP Lens API",
    description="Local API for the IP Lens prior-art triage application.",
    version="0.1.0",
)
app.include_router(router)
