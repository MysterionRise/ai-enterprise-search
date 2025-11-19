"""Main FastAPI application"""

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

from src.api.routes import analytics, auth, health, ingest, rag, recommendations, search
from src.core.config import settings

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)
REQUEST_DURATION = Histogram(
    "http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"]
)
SEARCH_QUERIES = Counter("search_queries_total", "Total search queries")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Startup: Initialize connections, load models, etc.
    try:
        from src.core.database import db

        db.connect()
        logger.info("Database connection initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    yield

    # Shutdown: Cleanup
    logger.info("Shutting down application")
    try:
        from src.core.database import db

        db.close()
    except Exception:
        pass


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Secure, multilingual, context-aware enterprise search with RAG",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and track metrics"""
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Calculate duration
    duration = time.time() - start_time

    # Log request
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")

    # Update metrics
    REQUEST_COUNT.labels(
        method=request.method, endpoint=request.url.path, status=response.status_code
    ).inc()
    REQUEST_DURATION.labels(method=request.method, endpoint=request.url.path).observe(duration)

    return response


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.DEBUG else "An error occurred",
        },
    )


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix=f"{settings.API_V1_PREFIX}/auth", tags=["Authentication"])
app.include_router(search.router, prefix=f"{settings.API_V1_PREFIX}/search", tags=["Search"])
app.include_router(ingest.router, prefix=f"{settings.API_V1_PREFIX}/ingest", tags=["Ingestion"])
app.include_router(rag.router, tags=["RAG"])
app.include_router(recommendations.router, tags=["Recommendations"])
app.include_router(analytics.router, tags=["Analytics"])


# Prometheus metrics endpoint
@app.get("/metrics")
async def metrics():
    """Expose Prometheus metrics"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Serve static files
ui_dir = os.path.join(os.path.dirname(__file__), "..", "..", "ui")
if os.path.exists(os.path.join(ui_dir, "static")):
    app.mount("/static", StaticFiles(directory=os.path.join(ui_dir, "static")), name="static")


# Root endpoint - serve UI
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the search UI"""
    ui_file = os.path.join(ui_dir, "templates", "index.html")
    if os.path.exists(ui_file):
        with open(ui_file) as f:
            return HTMLResponse(content=f.read())
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }
