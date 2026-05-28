import base64
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.services.llm.schemas_llm import ParsedPrescription

_SYSTEM_PROMPT = (
    "You extract structured information from photographs of doctors' prescriptions. "
    "Read only what is visible in the image; do not invent or guess. Use null for "
    "any field you cannot determine. Dates must be valid ISO calendar dates and "
    "times must be 24-hour clock times."
)


@lru_cache(maxsize=1)
def _structured_llm():
    llm = ChatGoogleGenerativeAI(
        model=settings.GOOGLE_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0,
    )
    # Gemini supports structured output via LangChain's with_structured_output.
    return llm.with_structured_output(ParsedPrescription)


def parse_prescription_images(
    images: list[tuple[bytes, str]],
) -> ParsedPrescription:
    """Parse one prescription from one or more image pages.

    `images` is a list of (image_bytes, content_type). All pages are sent to
    the LLM in a single call so it can reason across them as one prescription.
    """
    if not images:
        raise ValueError("At least one image is required")

    instruction = (
        "Extract the prescription data. The following "
        f"{len(images)} image(s) are pages of a single prescription; merge "
        "their contents into one structured result."
    )
    content: list[dict] = [{"type": "text", "text": instruction}]
    for image_bytes, content_type in images:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        data_url = f"data:{content_type};base64,{b64}"
        content.append({"type": "image_url", "image_url": {"url": data_url}})

    return _structured_llm().invoke(
        [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=content),
        ]
    )
