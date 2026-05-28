"""Pydantic schemas that define the structured output we ask the LLM for.

These are used with LangChain's `with_structured_output()` to ensure the
Gemini response validates against the expected schema.
"""

from datetime import date, time
from typing import Literal, Optional

from pydantic import BaseModel, Field


class MedicationSchedule(BaseModel):
    """Machine-readable schedule. The reminder scheduler will read ONLY these fields."""

    times_per_day: Optional[int] = Field(description="The total number of times per day the medication should be taken (e.g., TID = 3).")
    specific_times: list[time] = Field(default_factory=list, description="List of explicit clock times mentioned (e.g., '10:00 PM').")
    interval_hours: Optional[int] = Field(description="The number of hours between doses if specified as an interval (e.g., 'Every 6 hours' = 6).")
    duration_days: Optional[int] = Field(description="Total duration of treatment converted into number of days (e.g., '2 weeks' = 14).")
    with_food: Optional[Literal["before", "after", "with", "any"]] = Field(description="Relationship to meals. Map abbreviations: AC/Before meals -> 'before'; PC/After meals -> 'after'.")
    as_needed: bool = Field(description="Set to True if marked as PRN, as needed, SOS or when required. Default is False.")
    notes: Optional[str] = Field(description="Any specific scheduling nuances not covered by other fields.")


class Medication(BaseModel):
    name: str = Field(description="The commercial brand name or generic chemical name of the prescribed drug or supplement (e.g., 'Amoxicillin').")
    dosage: Optional[str] = Field(description="The strength or quantity per individual dose, including units (e.g., '500 mg', '10 mL', '1 tablet').")
    route: Optional[str] = Field(description="The method/pathway by which the medication enters the body (e.g., 'Oral', 'Topical', 'Intravenous', 'Ophthalmic', 'Subcutaneous'). Translate abbreviations like 'PO' to 'Oral'.")
    raw_frequency: Optional[str] = Field(description="The exact, verbatim frequency text written by the doctor on the script before any translation or parsing happens (e.g., '1-0-1', 'TID AC', 'BD', 'Once daily').")
    schedule: MedicationSchedule = Field(default_factory=MedicationSchedule, description="The structured, machine-readable breakdown of the frequency and timing rules extracted from the prescription.")
    instructions: Optional[str] = Field(description="Special warnings, administration advice, or non-scheduling instructions written for this specific drug (e.g., 'Do not crush', 'Avoid alcohol', 'Finish the entire course').")


class DiagnosticTest(BaseModel):
    name: str = Field(description="The exact name of the laboratory test, imaging, scan, or clinical investigation ordered by the physician (e.g., 'Complete Blood Count (CBC)', 'Chest X-Ray', 'HbA1c').")
    instructions: Optional[str] = Field(description="Any preparation guidelines or instructions specific to this test (e.g., '12 hours fasting required', 'Drink 1 liter of water 1 hour prior').")


class ParsedPrescription(BaseModel):
    patient_name: Optional[str] = Field(description="The full legal name of the patient as written on the document header. Use null if obscured or completely unreadable.")
    patient_age: Optional[str] = Field(description="The age of the patient captured exactly as written, retaining any units specified (e.g., '45', '28 Yrs', '6 months').")
    doctor_name: Optional[str] = Field(description="The full name of the issuing physician, doctor, or medical practitioner, excluding standard generic titles like 'MD' unless part of how they signed.")
    prescription_date: Optional[date] = Field(description="The exact date the prescription was written or issued, formatted strictly as an ISO date (YYYY-MM-DD).")
    diagnosis: Optional[str] = Field(description="The clinical diagnosis, symptoms, indications, or medical conditions noted by the doctor as the reason for the visit (e.g., 'Acute Pharyngitis', 'Hypertension').")
    medications: list[Medication] = Field(default_factory=list, description="A list of all distinct therapeutic drugs, vitamins, or medical supplements prescribed to the patient. Leave empty if none are listed.")
    diagnostic_tests: list[DiagnosticTest] = Field(default_factory=list, description="A list of all laboratory work, imaging requests, or diagnostic procedures ordered on the script. Leave empty if none are listed.")
    follow_up_date: Optional[date] = Field(description="The calculated or explicitly written specific next appointment date formatted as an ISO date (YYYY-MM-DD). If written as a timeline relative to the prescription date (e.g., 'Review in 2 weeks'), calculate the exact calendar date.")
    additional_notes: Optional[str] = Field(description="Any overall document notes, generic hospital/clinic warnings, vital signs recorded on the page (e.g., 'BP: 120/80'), or miscellaneous information not captured elsewhere.")
