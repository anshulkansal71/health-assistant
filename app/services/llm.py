import base64
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import settings
from app.schemas_llm import ParsedPrescription

_SYSTEM_PROMPT = (
    "You extract structured information from photographs of doctors' prescriptions. "
    "Read only what is visible in the image; do not invent or guess. Use null for "
    "any field you cannot determine. Dates must be valid ISO calendar dates and "
    "times must be 24-hour clock times."
)


@lru_cache(maxsize=1)
def _structured_llm():
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )
    # method="json_schema" + strict=True maps to OpenAI's strict Structured
    # Outputs, so the response is guaranteed to validate against ParsedPrescription.
    return llm.with_structured_output(
        ParsedPrescription, method="json_schema", strict=True
    )


def parse_prescription_image(
    image_bytes: bytes, content_type: str
) -> ParsedPrescription:
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{content_type};base64,{b64}"

    return _structured_llm().invoke(
        [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(
                content=[
                    {"type": "text", "text": "Extract the prescription data."},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]
            ),
        ]
    )
