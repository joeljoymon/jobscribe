from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.routers import jobs
import os

Base.metadata.create_all(bind=engine)

os.makedirs("uploads", exist_ok=True)

app = FastAPI(
    title="JobScribe",
    description="Track job applications with AI-powered resume analysis",
    version="0.1.0"
)

app.include_router(jobs.router)

@app.get("/")
def root():
    return {
        "message": "JobScribe is running",
        "docs": "Visit /docs to see all endpoints"
    }