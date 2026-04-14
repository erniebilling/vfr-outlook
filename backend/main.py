import os
from dotenv import load_dotenv

load_dotenv()

# Configure OpenTelemetry before anything else so auto-instrumentation patches
# libraries (httpx, etc.) at import time.
from otel import configure_otel
configure_otel()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from routers import airport

app = FastAPI(
    title="VFR Outlook API",
    description="VFR probability forecasts for GA pilots",
    version="0.1.0",
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
FastAPIInstrumentor.instrument_app(app)
HTTPXClientInstrumentor().instrument()


@app.get("/health")
async def health():
    return {"status": "ok"}
