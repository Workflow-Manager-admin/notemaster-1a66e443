from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .models import Base
from .database import engine

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PUBLIC_INTERFACE
@app.on_event("startup")
def on_startup():
    """Create database tables if they do not exist (dev only). For production, use Alembic migrations."""
    Base.metadata.create_all(bind=engine)

@app.get("/")
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}
