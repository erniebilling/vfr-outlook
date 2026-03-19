from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import airport

app = FastAPI(
    title="VFR Watch API",
    description="VFR probability forecasts for GA pilots",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(airport.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
