"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.api import router

app = FastAPI(
    title="IP Lens API",
    description="Local API for the IP Lens prior-art triage application.",
    version="0.1.0",
)
app.include_router(router)


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request,
    exc: RequestValidationError,
):
    """Use 400 for malformed analysis requests; retain FastAPI defaults elsewhere."""
    if request.url.path == "/api/analyses":
        return JSONResponse(
            status_code=400,
            content={"detail": "Invalid analysis request."},
        )
    return await request_validation_exception_handler(request, exc)
