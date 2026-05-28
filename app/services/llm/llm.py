import base64
from functools import lru_cache

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings
from app.services.llm.schemas_llm import ParsedPrescription

_SYSTEM_PROMPT = (
  """ ROLE & OBJECTIVE:
You are an expert medical data extraction assistant specializing in Clinical OCR. Your task is to accurately analyze the provided photograph of a doctor's prescription (which may contain handwritten text, typed text, abbreviations, and medical jargon) and extract the information into the requested structured schema.

EXTRACTION PRINCIPLES & GUARDRAILS:
1. STRICT TRUTH-FULNESS: Rely ONLY on the visual evidence in the image. Do not invent, assume, or extrapolate information. If a field is not explicitly present or cannot be confidently read, set it to `null` or an empty list as defined by the schema.
2. MEDICAL ABBREVIATIONS: Translate standard medical/Latin abbreviations into clear English where applicable for the fields (e.g., "PO" to "Oral", "TID" or "t.i.d." to 3 times per day). 
3. DATES & TIMES: 
 - Convert all dates into valid ISO calendar dates (YYYY-MM-DD). If the year is ambiguous, use the most contextually logical current year or leave as null if unsafe to assume.
 - Convert all specific times to 24-hour clock formats (HH:MM:SS).
 
 FIELD-SPECIFIC EXTRACTION INSTRUCTIONS:

- patient_age: Extract exactly as written (e.g., "45", "6 months", "34 Yrs").
- medications: Identify every distinct drug or supplement listed.
    * name: The brand or generic name of the medicine.
    * dosage: The strength/volume per dose (e.g., "500mg", "10ml", "1 tablet").
    * route: How the medication is taken (e.g., "Oral", "Topical", "Intravenous").
    * raw_frequency: Capture the exact frequency phrase as written by the doctor before processing (e.g., "TID AC", "Once daily", "Every 8 hours").
    * schedule:
        - times_per_day: Calculate the total number of times a day the medicine is taken based on the frequency.
        - specific_times: If specific clock times or times of day are mentioned (e.g., "at 9 AM and 9 PM"), map them to 24-hour times.
        - interval_hours: If a numeric hourly interval is given (e.g., "Every 6 hours"), extract the number (6).
        - duration_days: The total number of days the medication should be taken. Convert weeks/months to total days if clear (e.g., "2 weeks" = 14).
        - with_food: Map to "before", "after", "with", or "any" based on context (e.g., "AC" / "Before food" -> "before"; "PC" / "After meals" -> "after").
        - as_needed: Set to True if marked as "PRN", "pro re nata", "whenever required", or "as needed". Otherwise, default to False.
        - notes: Any specific scheduling nuances not covered by the other fields.
    * instructions: Any other specific advice regarding the medication (e.g., "Avoid alcohol", "Finish the full course").

- diagnostic_tests: Extract any lab tests, radiology, or investigations ordered (e.g., "CBC", "X-Ray Chest", "HbA1c").
- follow_up_date: Look for phrases like "Review after 1 week" or "Return on [Date]" and convert to a valid ISO date if a specific date can be calculated or is explicitly written.

Take a deep breath, review the prescription image meticulously step-by-step, and map the extracted data into the requested Pydantic schema structure.
  """
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
