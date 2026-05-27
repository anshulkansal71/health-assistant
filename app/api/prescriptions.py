from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app import models, schemas
from app.config import settings
from app.database import get_db
from app.services import llm, s3

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/pjpeg"}


def _get_or_404(db: Session, prescription_id: UUID) -> models.Prescription:
    p = (
        db.query(models.Prescription)
        .filter(models.Prescription.id == prescription_id)
        .first()
    )
    if not p:
        raise HTTPException(status_code=404, detail="Prescription not found")
    return p


@router.post(
    "",
    response_model=schemas.PrescriptionRead,
    status_code=201,
    summary="Upload a JPEG prescription, parse it with the LLM, and store it",
)
async def create_prescription(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Only JPEG images are accepted (got {file.content_type!r})",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    s3_key = s3.upload_prescription(
        image_bytes,
        file.content_type,
        file.filename or "prescription.jpg",
    )

    try:
        parsed = llm.parse_prescription_image(image_bytes, file.content_type)
    except Exception as exc:
        try:
            s3.delete_prescription(s3_key)
        except Exception:
            pass
        raise HTTPException(
            status_code=502, detail=f"LLM parsing failed: {exc}"
        ) from exc

    prescription = models.Prescription(
        s3_key=s3_key,
        original_filename=file.filename,
        content_type=file.content_type,
        patient_name=parsed.patient_name,
        patient_age=parsed.patient_age,
        doctor_name=parsed.doctor_name,
        prescription_date=parsed.prescription_date,
        diagnosis=parsed.diagnosis,
        follow_up_date=parsed.follow_up_date,
        additional_notes=parsed.additional_notes,
        raw_llm_response=parsed.model_dump(mode="json"),
    )
    for med in parsed.medications:
        if not med.name:
            continue
        prescription.medications.append(
            models.Medication(
                name=med.name,
                dosage=med.dosage,
                route=med.route,
                raw_frequency=med.raw_frequency,
                instructions=med.instructions,
                times_per_day=med.schedule.times_per_day,
                specific_times=list(med.schedule.specific_times),
                interval_hours=med.schedule.interval_hours,
                duration_days=med.schedule.duration_days,
                with_food=med.schedule.with_food,
                as_needed=med.schedule.as_needed,
                schedule_notes=med.schedule.notes,
            )
        )
    for test in parsed.diagnostic_tests:
        if not test.name:
            continue
        prescription.diagnostic_tests.append(
            models.DiagnosticTest(name=test.name, instructions=test.instructions)
        )

    db.add(prescription)
    db.commit()
    db.refresh(prescription)
    return prescription


@router.get("", response_model=list[schemas.PrescriptionRead])
def list_prescriptions(
    patient_name: Optional[str] = Query(None),
    doctor_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(models.Prescription)
    if patient_name:
        q = q.filter(models.Prescription.patient_name.ilike(f"%{patient_name}%"))
    if doctor_name:
        q = q.filter(models.Prescription.doctor_name.ilike(f"%{doctor_name}%"))
    return q.order_by(models.Prescription.created_at.desc()).all()


@router.get("/{prescription_id}", response_model=schemas.PrescriptionRead)
def get_prescription(prescription_id: UUID, db: Session = Depends(get_db)):
    return _get_or_404(db, prescription_id)


@router.get(
    "/{prescription_id}/image-url",
    response_model=schemas.PresignedImageUrl,
    summary="Generate a short-lived presigned URL to view the original JPEG",
)
def get_image_url(prescription_id: UUID, db: Session = Depends(get_db)):
    p = _get_or_404(db, prescription_id)
    url = s3.generate_presigned_url(p.s3_key, settings.PRESIGNED_URL_EXPIRY_SECONDS)
    return schemas.PresignedImageUrl(
        url=url, expires_in_seconds=settings.PRESIGNED_URL_EXPIRY_SECONDS
    )


@router.put("/{prescription_id}", response_model=schemas.PrescriptionRead)
def update_prescription(
    prescription_id: UUID,
    update: schemas.PrescriptionUpdate,
    db: Session = Depends(get_db),
):
    p = _get_or_404(db, prescription_id)
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{prescription_id}", status_code=204)
def delete_prescription(prescription_id: UUID, db: Session = Depends(get_db)):
    p = _get_or_404(db, prescription_id)
    s3_key = p.s3_key
    db.delete(p)
    db.commit()
    try:
        s3.delete_prescription(s3_key)
    except Exception:
        pass
