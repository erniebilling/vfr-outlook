import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

# Configure OpenTelemetry before anything else so auto-instrumentation patches
# libraries (httpx, etc.) at import time.
from otel import configure_otel
configure_otel()

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from routers import airport


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Shared HTTP client — one connection pool for all outbound weather API
    # calls.  Keeps TCP connections warm across requests and makes per-request
    # connection overhead negligible during region/trip fan-outs.
    async with httpx.AsyncClient(
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
        timeout=httpx.Timeout(15.0),
    ) as client:
        app.state.http_client = client
        yield


app = FastAPI(
    title="VFR Outlook API",
    description="VFR probability forecasts for GA pilots",
    version="0.1.0",
    lifespan=lifespan,
)

_default_origins = "http://localhost:5173,http://localhost:3000"
allow_origins = os.environ.get("CORS_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(airport.router)

# Instrument FastAPI (adds server-side spans for every request) and httpx
# (propagates trace context to outbound weather API calls).
FastAPIInstrumentor.instrument_app(app, excluded_urls="/health")
HTTPXClientInstrumentor().instrument()


@app.get("/health")
async def health():
    return {"status": "ok"}
