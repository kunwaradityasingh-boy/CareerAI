from fastapi import FastAPI

from backend.database import Base, engine
from backend import models

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="CareerAI API",
    description="AI-Powered Career & Placement Intelligence Platform",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "message": "CareerAI API is running!",
        "status": "success",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
    }