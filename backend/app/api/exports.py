"""Export endpoints."""

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.analytics.filters import common_filters
from app.auth.deps import require_role
from app.db.session import get_db
from app.exports.bundle import build_bundle
from app.models.entities import AuditLog, User

router = APIRouter(tags=["exports"])


@router.get("/exports/power-bi")
def power_bi_export(
    f: dict = Depends(common_filters),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "analyst", "viewer")),
):
    # Viewers may export approved reports; the bundle only holds cleaned data.
    active = {k: v for k, v in f.items() if v}
    db.add(
        AuditLog(
            user_id=user.id,
            action="export_powerbi",
            entity="export",
            entity_id="power-bi-bundle",
            meta={"filters": active},
        )
    )
    db.commit()
    data = build_bundle(db, f)
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=insightforge_powerbi.zip"},
    )
