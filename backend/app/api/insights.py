"""Executive insights endpoint."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.analytics.filters import common_filters, resolve_period
from app.auth.deps import get_current_user
from app.db.session import get_db
from app.insights.engine import generate as generate_insights
from app.models.entities import User

router = APIRouter(tags=["insights"])


@router.get("/insights")
def insights(
    f: dict = Depends(common_filters),
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    cf, ct, pf, pt = resolve_period(f)
    items = generate_insights(db, f, cf, ct, pf, pt)
    return {
        "period": {
            "from": str(cf) if cf else None,
            "to": str(ct) if ct else None,
            "prev_from": str(pf) if pf else None,
            "prev_to": str(pt) if pt else None,
        },
        "count": len(items),
        "generated_at": datetime.now(UTC).isoformat(),
        "insights": items,
    }
