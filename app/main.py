from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.services.db import models
from app.api import prescriptions
from app.services.db.database import engine
from app.tracing import setup_tracing

# Simple bootstrap: create tables on startup. Swap for Alembic if/when migrations
# matter.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Health Assistant",
    description="Upload doctors' prescriptions, parse them with Gemini 3.1 Pro, and store "
    "the structured data for downstream reminders.",
    version="0.1.0",
)

# Initialise Arize tracing (LangChain + FastAPI instrumentation).
# Must happen after the app is created but before requests are served.
setup_tracing(app)

app.include_router(prescriptions.router)



def _rewrite_binary_media_type(node):
    # Pydantic v2 / OpenAPI 3.1 emits binary uploads as
    #   {"type": "string", "contentMediaType": "application/octet-stream"}
    # which Swagger UI does not render as a file picker (especially inside arrays).
    # Rewrite to the OpenAPI 3.0-style {"type": "string", "format": "binary"} that
    # Swagger UI understands.
    if isinstance(node, dict):
        if node.get("contentMediaType") == "application/octet-stream":
            node.pop("contentMediaType", None)
            node["format"] = "binary"
        for v in node.values():
            _rewrite_binary_media_type(v)
    elif isinstance(node, list):
        for v in node:
            _rewrite_binary_media_type(v)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    _rewrite_binary_media_type(schema)
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi


@app.get("/health")
def health():
    return {"status": "ok"}
