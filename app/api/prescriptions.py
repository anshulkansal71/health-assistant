from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app import schemas
from app.config import settings
from app.services.db import models
from app.services.db.database import get_db
from app.services.llm import llm
from app.services import s3

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
    summary="Upload one or more JPEG pages of a prescription, parse them with the LLM, and store them",
)
async def create_prescription(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required")

    images: list[tuple[bytes, str, str]] = []  # (bytes, content_type, filename)
    for file in files:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Only JPEG images are accepted (got {file.content_type!r} "
                    f"for {file.filename!r})"
                ),
            )
        data = await file.read()
        if not data:
            raise HTTPException(
                status_code=400,
                detail=f"Uploaded file {file.filename!r} is empty",
            )
        images.append((data, file.content_type, file.filename or "prescription.jpg"))

    s3_keys: list[str] = []
    try:
        for data, content_type, filename in images:
            s3_keys.append(s3.upload_prescription(data, content_type, filename))
    except Exception:
        for key in s3_keys:
            try:
                s3.delete_prescription(key)
            except Exception:
                pass
        raise

    try:
        parsed = llm.parse_prescription_images(
            [(data, ct) for data, ct, _ in images]
        )
    except Exception as exc:
        for key in s3_keys:
            try:
                s3.delete_prescription(key)
            except Exception:
                pass
        raise HTTPException(
            status_code=502, detail=f"LLM parsing failed: {exc}"
        ) from exc

    prescription = models.Prescription(
        patient_name=parsed.patient_name,
        patient_age=parsed.patient_age,
        doctor_name=parsed.doctor_name,
        prescription_date=parsed.prescription_date,
        diagnosis=parsed.diagnosis,
        follow_up_date=parsed.follow_up_date,
        additional_notes=parsed.additional_notes,
        raw_llm_response=parsed.model_dump(mode="json"),
    )
    for s3_key, (_, content_type, filename) in zip(s3_keys, images):
        prescription.images.append(
            models.PrescriptionImage(
                s3_key=s3_key,
                original_filename=filename,
                content_type=content_type,
            )
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
    "/{prescription_id}/image-urls",
    response_model=schemas.PresignedImageUrls,
    summary="Generate short-lived presigned URLs for every page of the prescription",
)
def get_image_urls(prescription_id: UUID, db: Session = Depends(get_db)):
    p = _get_or_404(db, prescription_id)
    expires = settings.PRESIGNED_URL_EXPIRY_SECONDS
    return schemas.PresignedImageUrls(
        expires_in_seconds=expires,
        images=[
            schemas.PresignedImageUrl(
                image_id=img.id,
                url=s3.generate_presigned_url(img.s3_key, expires),
                expires_in_seconds=expires,
            )
            for img in p.images
        ],
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
    s3_keys = [img.s3_key for img in p.images]
    db.delete(p)
    db.commit()
    for key in s3_keys:
        try:
            s3.delete_prescription(key)
        except Exception:
            pass
