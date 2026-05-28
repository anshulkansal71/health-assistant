import uuid

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    patient_name = Column(String, index=True)
    patient_age = Column(String)

    doctor_name = Column(String, index=True)

    prescription_date = Column(Date)
    diagnosis = Column(Text)
    follow_up_date = Column(Date)
    additional_notes = Column(Text)

    # Verbatim LLM output, kept for auditability and re-derivation.
    raw_llm_response = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    images = relationship(
        "PrescriptionImage",
        back_populates="prescription",
        cascade="all, delete-orphan",
        order_by="PrescriptionImage.created_at",
    )
    medications = relationship(
        "Medication",
        back_populates="prescription",
        cascade="all, delete-orphan",
    )
    diagnostic_tests = relationship(
        "DiagnosticTest",
        back_populates="prescription",
        cascade="all, delete-orphan",
    )


class PrescriptionImage(Base):
    __tablename__ = "prescription_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prescriptions.id", ondelete="CASCADE"),
        nullable=False,
    )

    s3_key = Column(String, nullable=False)
    original_filename = Column(String)
    content_type = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    prescription = relationship("Prescription", back_populates="images")


class Medication(Base):
    __tablename__ = "medications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prescriptions.id", ondelete="CASCADE"),
        nullable=False,
    )

    name = Column(String, nullable=False)
    dosage = Column(String)
    route = Column(String)
    raw_frequency = Column(String)
    instructions = Column(Text)

    # Flattened MedicationSchedule fields — the reminder scheduler will query
    # these directly.
    times_per_day = Column(Integer)
    specific_times = Column(ARRAY(Time))
    interval_hours = Column(Integer)
    duration_days = Column(Integer)
    with_food = Column(String)
    as_needed = Column(Boolean, nullable=False, default=False)
    schedule_notes = Column(Text)

    prescription = relationship("Prescription", back_populates="medications")

    @property
    def schedule(self) -> dict:
        # Lets Pydantic's from_attributes pick up a nested `schedule` object on read.
        return {
            "times_per_day": self.times_per_day,
            "specific_times": self.specific_times or [],
            "interval_hours": self.interval_hours,
            "duration_days": self.duration_days,
            "with_food": self.with_food,
            "as_needed": self.as_needed,
            "notes": self.schedule_notes,
        }


class DiagnosticTest(Base):
    __tablename__ = "diagnostic_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("prescriptions.id", ondelete="CASCADE"),
        nullable=False,
    )

    name = Column(String, nullable=False)
    instructions = Column(Text)

    prescription = relationship("Prescription", back_populates="diagnostic_tests")
