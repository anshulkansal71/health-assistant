from datetime import date, datetime, time
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MedicationScheduleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    times_per_day: Optional[int] = None
    specific_times: list[time] = []
    interval_hours: Optional[int] = None
    duration_days: Optional[int] = None
    with_food: Optional[Literal["before", "after", "with", "any"]] = None
    as_needed: bool = False
    notes: Optional[str] = None


class MedicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    dosage: Optional[str] = None
    route: Optional[str] = None
    raw_frequency: Optional[str] = None
    instructions: Optional[str] = None
    schedule: MedicationScheduleRead


class DiagnosticTestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    instructions: Optional[str] = None


class PrescriptionImageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: Optional[str] = None
    content_type: Optional[str] = None


class PrescriptionBase(BaseModel):
    patient_name: Optional[str] = None
    patient_age: Optional[str] = None
    doctor_name: Optional[str] = None
    prescription_date: Optional[date] = None
    diagnosis: Optional[str] = None
    follow_up_date: Optional[date] = None
    additional_notes: Optional[str] = None


class PrescriptionUpdate(PrescriptionBase):
    pass


class PrescriptionRead(PrescriptionBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    images: list[PrescriptionImageRead] = []
    medications: list[MedicationRead] = []
    diagnostic_tests: list[DiagnosticTestRead] = []


class PresignedImageUrl(BaseModel):
    image_id: UUID
    url: str
    expires_in_seconds: int


class PresignedImageUrls(BaseModel):
    expires_in_seconds: int
    images: list[PresignedImageUrl]
