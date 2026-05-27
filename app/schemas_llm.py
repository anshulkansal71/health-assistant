"""Pydantic schemas that define the structured output we ask the LLM for.

These are passed straight to `client.beta.chat.completions.parse(response_format=...)`,
so the OpenAI SDK enforces the shape and hands us back validated objects.
"""

from datetime import date, time
from typing import Literal, Optional

from pydantic import BaseModel, Field


class MedicationSchedule(BaseModel):
    """Machine-readable schedule. The reminder scheduler will read ONLY these fields."""

    times_per_day: Optional[int] = None
    specific_times: list[time] = Field(default_factory=list)
    interval_hours: Optional[int] = None
    duration_days: Optional[int] = None
    with_food: Optional[Literal["before", "after", "with", "any"]] = None
    as_needed: bool = False
    notes: Optional[str] = None


class Medication(BaseModel):
    name: str
    dosage: Optional[str] = None
    route: Optional[str] = None
    raw_frequency: Optional[str] = None
    schedule: MedicationSchedule = Field(default_factory=MedicationSchedule)
    instructions: Optional[str] = None


class DiagnosticTest(BaseModel):
    name: str
    instructions: Optional[str] = None


class ParsedPrescription(BaseModel):
    patient_name: Optional[str] = None
    patient_age: Optional[str] = None
    doctor_name: Optional[str] = None
    prescription_date: Optional[date] = None
    diagnosis: Optional[str] = None
    medications: list[Medication] = Field(default_factory=list)
    diagnostic_tests: list[DiagnosticTest] = Field(default_factory=list)
    follow_up_date: Optional[date] = None
    additional_notes: Optional[str] = None
