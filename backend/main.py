from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import engine
from backend.routers.auth import router as auth_router
from backend.routers.student_profile import router as student_profile_router
from backend.routers.resume import router as resume_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Database schema is managed by Alembic.
    yield


app = FastAPI(
    title="CareerAI API",
    description="AI-Powered Career & Placement Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Development frontend origins only.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router)
app.include_router(student_profile_router)
app.include_router(resume_router)


@app.get("/")
def root():
    return {
        "message": "CareerAI API is running!",
        "status": "success",
    }


@app.get("/health")
def health_check():
    try:
        with engine.connect():
            return {
                "status": "healthy",
                "database": "connected",
            }
    except Exception:
        return {
            "status": "unhealthy",
            "database": "disconnected",
        }
