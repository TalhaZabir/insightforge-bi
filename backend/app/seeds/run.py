"""Seed runner: demo users + full dim_date calendar. Idempotent.

Usage (from backend/):
    python -m app.seeds.run
"""

from datetime import date, timedelta

from app.auth.security import hash_password
from app.db.session import SessionLocal
from app.models.entities import DimDate, User

DEMO_USERS = [
    ("admin@insightforge.io", "Admin123!", "admin"),
    ("analyst@insightforge.io", "Analyst123!", "analyst"),
    ("viewer@insightforge.io", "Viewer123!", "viewer"),
]

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def seed_users(db) -> int:
    created = 0
    for email, password, role in DEMO_USERS:
        if db.query(User).filter(User.email == email).first():
            continue
        db.add(User(email=email, hashed_password=hash_password(password), role=role))
        created += 1
    db.commit()
    return created


def seed_calendar(db, start: date = date(2023, 1, 1), end: date = date(2026, 12, 31)) -> int:
    added = 0
    d = start
    batch = []
    while d <= end:
        if db.query(DimDate).filter(DimDate.date_key == int(d.strftime("%Y%m%d"))).first():
            d += timedelta(days=1)
            continue
        batch.append(
            DimDate(
                date_key=int(d.strftime("%Y%m%d")),
                date=d,
                year=d.year,
                quarter=(d.month - 1) // 3 + 1,
                month=d.month,
                month_name=MONTHS[d.month],
                day=d.day,
                weekday=d.weekday(),
                weekday_name=WEEKDAYS[d.weekday()],
                is_weekend=d.weekday() >= 5,
            )
        )
        added += 1
        if len(batch) >= 500:
            db.add_all(batch)
            db.commit()
            batch = []
        d += timedelta(days=1)
    if batch:
        db.add_all(batch)
        db.commit()
    return added


def reset_db(db) -> int:
    """Delete all application data (keeps schema/alembic version). FK-safe order."""
    from app.models import entities as m

    total = 0
    for model in (
        m.FactSale,
        m.RejectedRecord,
        m.ValidationResult,
        m.RawSalesRecord,
        m.ImportJob,
        m.UploadedFile,
        m.AuditLog,
        m.DimChannel,
        m.DimCustomer,
        m.DimDate,
        m.DimProduct,
        m.DimRegion,
        m.DimRep,
        m.User,
    ):
        total += db.query(model).delete(synchronize_session=False)
    db.commit()
    return total


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="wipe all application data before seeding")
    args = ap.parse_args()
    db = SessionLocal()
    try:
        if args.reset:
            print(f"reset: deleted {reset_db(db)} rows")
        u = seed_users(db)
        c = seed_calendar(db)
        print(f"seed done: users_created={u} dates_added={c}")
        print("demo logins: admin@insightforge.io/Admin123! analyst/Analyst123! viewer/Viewer123!")
    finally:
        db.close()


if __name__ == "__main__":
    main()
