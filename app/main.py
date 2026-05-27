from fastapi import FastAPI

from app import models
from app.api import prescriptions
from app.database import engine

# Simple bootstrap: create tables on startup. Swap for Alembic if/when migrations
# matter.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Health Assistant",
    description="Upload doctors' prescriptions, parse them with GPT-4o, and store "
    "the structured data for downstream reminders.",
    version="0.1.0",
)

app.include_router(prescriptions.router)


@app.get("/health")
def health():
    return {"status": "ok"}
