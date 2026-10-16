"""Upload / validation / cleaning / import endpoints."""

from __future__ import annotations

import csv
import io
import re
import uuid
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user, require_role
from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.ingestion.loader import load_cleaned_to_db
from app.ingestion.mapper import suggest_mapping
from app.ingestion.parser import SheetRequiredError, list_sheets, sha256_file
from app.ingestion.service import load_raw_frame, mapping_problems, run_cleaning, run_validation
from app.models.entities import (
    AuditLog,
    FactSale,
    ImportJob,
    RawSalesRecord,
    RejectedRecord,
    UploadedFile,
    User,
    ValidationResult,
)
from app.schemas.ingestion import (
    CleanRequest,
    ConfirmRequest,
    JobOut,
    PreviewRequest,
    UploadResponse,
    ValidateRequest,
)

router = APIRouter(tags=["ingestion"])

# Overridable in tests so background confirmation hits the test database.
SessionFactory = SessionLocal

ALLOWED_EXT = {".csv", ".xlsx", ".xls"}
ALLOWED_MIME = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
}


def _upload_dir() -> Path:
    d = Path(settings.UPLOAD_DIR)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sanitize(name: str) -> str:
    base = Path(name).name
    return re.sub(r"[^A-Za-z0-9._-]", "_", base)[:120] or "upload"


def _audit(
    db: Session,
    user: User | None,
    action: str,
    entity: str,
    entity_id: str,
    meta: dict | None = None,
):
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            entity=entity,
            entity_id=entity_id,
            meta=meta or {},
        )
    )


def _job_or_404(db: Session, job_id: str) -> ImportJob:
    job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Import job not found")
    return job


def _to_jsonable(df: pd.DataFrame) -> list[dict]:
    recs = []
    for rec in df.to_dict("records"):
        clean: dict = {}
        for k, v in rec.items():
            if v is None or (not isinstance(v, str) and pd.isna(v)):
                clean[k] = None
            elif hasattr(v, "item"):
                try:
                    clean[k] = v.item()
                except (ValueError, AttributeError):
                    clean[k] = str(v)
            else:
                clean[k] = v
        recs.append(clean)
    return recs


# ---------------- upload ----------------


@router.post("/uploads", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
def upload_file(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXT:
        raise HTTPException(
            status_code=400, detail=f"Unsupported extension '{suffix}'. Use CSV or XLSX."
        )
    if file.content_type and file.content_type not in ALLOWED_MIME:
        raise HTTPException(status_code=400, detail=f"Unsupported MIME type '{file.content_type}'")
    safe = _sanitize(file.filename or "upload")
    stored = _upload_dir() / f"{uuid.uuid4().hex}_{safe}"
    size = 0
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    with open(stored, "wb") as out:
        while chunk := file.file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                out.close()
                stored.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_MB} MB limit"
                )
            out.write(chunk)
    digest = sha256_file(stored)
    dupe = db.query(UploadedFile).filter(UploadedFile.file_hash == digest).first()
    if dupe:
        stored.unlink(missing_ok=True)
        raise HTTPException(
            status_code=409, detail=f"Duplicate of previously uploaded file '{dupe.filename}'"
        )
    try:
        sheets = list_sheets(stored)
    except Exception:
        stored.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Could not read file structure") from None
    rec = UploadedFile(
        filename=safe,
        stored_path=str(stored),
        file_hash=digest,
        size_bytes=size,
        mime=file.content_type or "",
        sheets=sheets,
        uploaded_by=user.id,
    )
    db.add(rec)
    db.commit()
    _audit(db, user, "upload", "uploaded_file", rec.id, {"filename": safe, "size": size})
    db.commit()
    return UploadResponse(file_id=rec.id, filename=safe, size_bytes=size, sheets=sheets)


@router.get("/uploads")
def list_uploads(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    files = db.query(UploadedFile).order_by(UploadedFile.created_at.desc()).all()
    out = []
    for f in files:
        jobs = (
            db.query(ImportJob)
            .filter(ImportJob.file_id == f.id)
            .order_by(ImportJob.created_at.desc())
            .all()
        )
        out.append(
            {
                "file_id": f.id,
                "filename": f.filename,
                "size_bytes": f.size_bytes,
                "sheets": f.sheets,
                "created_at": f.created_at.isoformat() if f.created_at else None,
                "jobs": [{"id": j.id, "status": j.status, "stats": j.stats} for j in jobs],
            }
        )
    return out


@router.get("/uploads/{file_id}")
def get_upload(file_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    f = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if f is None:
        raise HTTPException(status_code=404, detail="File not found")
    jobs = (
        db.query(ImportJob)
        .filter(ImportJob.file_id == file_id)
        .order_by(ImportJob.created_at.desc())
        .all()
    )
    return {
        "file_id": f.id,
        "filename": f.filename,
        "size_bytes": f.size_bytes,
        "sheets": f.sheets,
        "mapping": None,
        "jobs": [JobOut.model_validate(j).model_dump() for j in jobs],
    }


@router.delete("/uploads/{file_id}")
def discard_upload(
    file_id: str,
    force: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    f = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if f is None:
        raise HTTPException(status_code=404, detail="File not found")
    jobs = db.query(ImportJob).filter(ImportJob.file_id == file_id).all()
    if any(j.status == "processing" for j in jobs):
        raise HTTPException(
            status_code=409, detail="Cannot delete: an import is currently processing"
        )
    confirmed_jobs = [j for j in jobs if j.status == "confirmed"]
    if confirmed_jobs and not force:
        raise HTTPException(
            status_code=409,
            detail="Cannot discard: a confirmed import exists for this file. "
            "Use DELETE /uploads/{id}?force=true to also delete confirmed dashboard data.",
        )
    deleted_facts = 0
    if confirmed_jobs and force:
        batch_ids = [j.batch_id for j in jobs if j.batch_id]
        if batch_ids:
            deleted_facts = (
                db.query(FactSale)
                .filter(FactSale.batch_id.in_(batch_ids))
                .delete(synchronize_session=False)
            )
    job_ids = [j.id for j in jobs]
    for model in (RawSalesRecord, ValidationResult, RejectedRecord):
        if job_ids:
            db.query(model).filter(model.job_id.in_(job_ids)).delete(synchronize_session=False)
    db.query(ImportJob).filter(ImportJob.file_id == file_id).delete(synchronize_session=False)
    db.delete(f)
    action = "delete_upload" if (confirmed_jobs and force) else "discard_upload"
    _audit(
        db,
        user,
        action,
        "uploaded_file",
        file_id,
        {"filename": f.filename, "forced": bool(confirmed_jobs and force),
         "deleted_facts": deleted_facts},
    )
    db.commit()
    Path(f.stored_path).unlink(missing_ok=True)
    if confirmed_jobs and force:
        return {"status": "deleted", "deleted_facts": deleted_facts}
    return {"status": "discarded"}


# ---------------- preview / validate / clean / confirm ----------------


@router.post("/uploads/{file_id}/preview")
def preview(
    file_id: str,
    body: PreviewRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    f = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if f is None:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        df, sheets = load_raw_frame(Path(f.stored_path), body.sheet)
    except SheetRequiredError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Could not parse file: {type(e).__name__}"
        ) from e
    sample = _to_jsonable(df.head(body.limit))
    return {
        "columns": list(df.columns),
        "total_rows": len(df),
        "sheets": sheets,
        "rows": sample,
        "suggested_mapping": suggest_mapping(list(df.columns)),
    }


@router.post("/uploads/{file_id}/validate")
def validate_file(
    file_id: str,
    body: ValidateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    f = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if f is None:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        df_raw, _ = load_raw_frame(Path(f.stored_path), body.sheet)
    except SheetRequiredError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Could not parse file: {type(e).__name__}"
        ) from e
    problems = mapping_problems(body.mapping, list(df_raw.columns))
    if problems:
        raise HTTPException(status_code=422, detail={"mapping_problems": problems})
    df_mapped, report = run_validation(df_raw, body.mapping)

    job = ImportJob(
        file_id=file_id,
        sheet_name=body.sheet,
        mapping=body.mapping,
        status="validated",
        stats={"validation": report.stats},
        created_by=user.id,
    )
    db.add(job)
    db.flush()
    # persist raw + validation rows (replace any previous for this job — it is new)
    db.add_all(
        [
            RawSalesRecord(
                job_id=job.id,
                row_num=int(r["_row_num"]),
                payload={k: v for k, v in r.items() if not k.startswith("_")},
            )
            for r in _to_jsonable(df_mapped)
        ]
    )
    db.add_all(
        [
            ValidationResult(
                job_id=job.id,
                row_num=i["row_num"],
                severity=i["severity"],
                rule=i["rule"],
                column_name=i["column"],
                message=i["message"],
            )
            for i in report.issues
        ]
    )
    _audit(db, user, "validate", "import_job", job.id, {"stats": report.stats})
    db.commit()
    return {
        "job_id": job.id,
        "status": job.status,
        "summary": report.stats,
        "issues": report.issues[:200],
        "issue_count": len(report.issues),
    }


@router.post("/uploads/{file_id}/clean")
def clean_file(
    file_id: str,
    body: CleanRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    job = _job_or_404(db, body.job_id)
    if job.file_id != file_id:
        raise HTTPException(status_code=400, detail="Job does not belong to this file")
    if job.status not in ("validated", "cleaned", "failed"):
        raise HTTPException(
            status_code=409, detail=f"Cannot clean a job with status '{job.status}'"
        )
    raws = (
        db.query(RawSalesRecord)
        .filter(RawSalesRecord.job_id == job.id)
        .order_by(RawSalesRecord.row_num)
        .all()
    )
    if not raws:
        raise HTTPException(status_code=400, detail="No raw records stored for this job")
    df_mapped = pd.DataFrame([r.payload for r in raws])
    df_mapped["_row_num"] = [r.row_num for r in raws]
    from app.ingestion.validator import validate as _validate

    report = _validate(df_mapped)
    outcome = run_cleaning(df_mapped, report)

    db.query(RejectedRecord).filter(RejectedRecord.job_id == job.id).delete(
        synchronize_session=False
    )
    rej_payloads = (
        _to_jsonable(outcome.rejected.drop(columns=["_rejection_reasons"], errors="ignore"))
        if len(outcome.rejected)
        else []
    )
    reasons = outcome.rejected["_rejection_reasons"].tolist() if len(outcome.rejected) else []
    rownums = outcome.rejected["_row_num"].tolist() if len(outcome.rejected) else []
    db.add_all(
        [
            RejectedRecord(job_id=job.id, row_num=int(rn), payload=p, reason=rs)
            for p, rs, rn in zip(rej_payloads, reasons, rownums, strict=True)
        ]
    )
    stats = dict(job.stats or {})
    stats["cleaning"] = {
        **outcome.summary,
        "transformations": outcome.transformations,
        "examples": outcome.examples,
    }
    job.stats, job.status = stats, "cleaned"
    _audit(db, user, "clean", "import_job", job.id, {"summary": outcome.summary})
    db.commit()
    return {
        "job_id": job.id,
        "status": job.status,
        "summary": outcome.summary,
        "transformations": outcome.transformations,
        "examples": outcome.examples,
    }


def _do_confirm(job_id: str, user_id: str):
    db = SessionFactory()
    try:
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if job is None or job.status != "processing":
            return
        raws = (
            db.query(RawSalesRecord)
            .filter(RawSalesRecord.job_id == job.id)
            .order_by(RawSalesRecord.row_num)
            .all()
        )
        df_mapped = pd.DataFrame([r.payload for r in raws])
        df_mapped["_row_num"] = [r.row_num for r in raws]
        from app.ingestion.validator import validate as _validate

        outcome = run_cleaning(df_mapped, _validate(df_mapped))
        from app.models.entities import FactSale

        db.query(FactSale).filter(FactSale.batch_id == job.batch_id).delete(
            synchronize_session=False
        )
        summary = load_cleaned_to_db(db, job, outcome.cleaned)
        stats = dict(job.stats or {})
        stats["confirmation"] = summary
        job.stats, job.status = stats, "confirmed"
        db.add(
            AuditLog(
                user_id=user_id,
                action="confirm_import",
                entity="import_job",
                entity_id=job.id,
                meta=summary,
            )
        )
        db.commit()
    except Exception as e:  # noqa: BLE001 — job must reflect failure, never leak trace
        db.rollback()
        job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if job is not None:
            job.status, job.error = "failed", f"{type(e).__name__}"
            db.commit()
    finally:
        db.close()


@router.post("/uploads/{file_id}/confirm")
def confirm_file(
    file_id: str,
    body: ConfirmRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    job = _job_or_404(db, body.job_id)
    if job.file_id != file_id:
        raise HTTPException(status_code=400, detail="Job does not belong to this file")
    if job.status not in ("cleaned", "failed"):
        raise HTTPException(
            status_code=409, detail=f"Only cleaned jobs can be confirmed (status='{job.status}')"
        )
    job.status, job.error = "processing", None
    db.commit()
    background.add_task(_do_confirm, job.id, user.id)
    _audit(db, user, "confirm_start", "import_job", job.id, {})
    db.commit()
    return {"job_id": job.id, "status": "processing"}


# ---------------- job status / cancel / quality ----------------


@router.get("/imports/{job_id}/status", response_model=JobOut)
def job_status(job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _job_or_404(db, job_id)


@router.post("/imports/{job_id}/cancel")
def cancel_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst")),
):
    job = _job_or_404(db, job_id)
    if job.status in ("confirmed", "processing"):
        raise HTTPException(status_code=409, detail=f"Cannot cancel a '{job.status}' job")
    job.status = "cancelled"
    _audit(db, user, "cancel_import", "import_job", job.id, {})
    db.commit()
    return {"job_id": job.id, "status": job.status}


@router.get("/data-quality/{job_id}")
def data_quality(
    job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    job = _job_or_404(db, job_id)
    issues = (
        db.query(ValidationResult)
        .filter(ValidationResult.job_id == job_id)
        .order_by(ValidationResult.row_num)
        .limit(500)
        .all()
    )
    by_rule: dict[str, int] = {}
    for i in db.query(ValidationResult).filter(ValidationResult.job_id == job_id).all():
        by_rule[f"{i.severity}:{i.rule}"] = by_rule.get(f"{i.severity}:{i.rule}", 0) + 1
    stats = dict(job.stats or {})
    return {
        "job_id": job.id,
        "status": job.status,
        "validation": stats.get("validation"),
        "cleaning": stats.get("cleaning"),
        "confirmation": stats.get("confirmation"),
        "issues_by_rule": by_rule,
        "issues_sample": [
            {
                "row_num": i.row_num,
                "severity": i.severity,
                "rule": i.rule,
                "column": i.column_name,
                "message": i.message,
            }
            for i in issues
        ],
    }


@router.get("/data-quality/{job_id}/rejections.csv")
def rejections_csv(
    job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    _job_or_404(db, job_id)
    rows = (
        db.query(RejectedRecord)
        .filter(RejectedRecord.job_id == job_id)
        .order_by(RejectedRecord.row_num)
        .all()
    )
    buf = io.StringIO()
    if rows:
        cols = sorted({k for r in rows for k in (r.payload or {}).keys()})
        w = csv.DictWriter(buf, fieldnames=["row_num", *cols, "rejection_reason"])
        w.writeheader()
        for r in rows:
            w.writerow({"row_num": r.row_num, **(r.payload or {}), "rejection_reason": r.reason})
    else:
        buf.write("row_num,rejection_reason\n")
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=rejections_{job_id}.csv"},
    )
