import os
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()
from fastapi.middleware.cors import CORSMiddleware
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


@app.get("/health")
async def health():
    return {"status": "ok"}
