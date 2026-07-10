"""
main.py
--------
FastAPI application entrypoint.

Responsibilities:
  - Create the FastAPI app instance
  - Configure CORS so the React frontend (different port) can call this API
  - Register all route modules
  - Provide a simple health-check endpoint

Run with:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import video_routes, chat_routes

app = FastAPI(
    title="NoteTube AI",
    description="RAG-based YouTube video learning assistant API",
    version="1.0.0",
)

# --- CORS setup ---
# The React dev server runs on a different port (e.g. localhost:5173) than
# FastAPI (localhost:8000). Browsers block cross-origin requests by default,
# so we explicitly allow our frontend's origin here.
app.add_middleware(
    CORSMiddleware,
   allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register routers ---
app.include_router(video_routes.router)
app.include_router(chat_routes.router)


@app.get("/")
def health_check():
    """Simple endpoint to verify the API is running."""
    return {
        "status": "ok",
        "service": "NoteTube AI backend",
    }
