"""SQLAlchemy models — raw ingestion + star schema + auth/audit."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="viewer")  # admin|analyst|viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    mime: Mapped[str] = mapped_column(String(128), default="")
    sheets: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    jobs: Mapped[list[ImportJob]] = relationship("ImportJob", back_populates="file")


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    file_id: Mapped[str] = mapped_column(String(36), ForeignKey("uploaded_files.id"))
    sheet_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mapping: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    batch_id: Mapped[str] = mapped_column(String(36), unique=True, default=_uuid)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    file: Mapped[UploadedFile] = relationship("UploadedFile", back_populates="jobs")


class RawSalesRecord(Base):
    __tablename__ = "raw_sales_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_jobs.id"), index=True)
    row_num: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (Index("ix_raw_job_row", "job_id", "row_num"),)


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_jobs.id"), index=True)
    row_num: Mapped[int] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(10))  # error|warning
    rule: Mapped[str] = mapped_column(String(80))
    column_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    message: Mapped[str] = mapped_column(Text)


class RejectedRecord(Base):
    __tablename__ = "rejected_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("import_jobs.id"), index=True)
    row_num: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity: Mapped[str | None] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class MonthlyTarget(Base):
    """Monthly revenue/profit targets (single-org; month = YYYY-MM-01)."""

    __tablename__ = "monthly_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    month: Mapped[date] = mapped_column(Date, unique=True, index=True)
    revenue_target: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    profit_target: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


# ---------------- Dimensions ----------------


class DimDate(Base):
    __tablename__ = "dim_date"

    date_key: Mapped[int] = mapped_column(Integer, primary_key=True)  # YYYYMMDD
    date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    quarter: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer, index=True)
    month_name: Mapped[str] = mapped_column(String(12))
    day: Mapped[int] = mapped_column(Integer)
    weekday: Mapped[int] = mapped_column(Integer)  # 0=Mon
    weekday_name: Mapped[str] = mapped_column(String(12))
    is_weekend: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))


class DimCustomer(Base):
    __tablename__ = "dim_customer"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    segment: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DimProduct(Base):
    __tablename__ = "dim_product"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    product_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    subcategory: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DimRegion(Base):
    __tablename__ = "dim_region"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region: Mapped[str] = mapped_column(String(120), index=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)

    __table_args__ = (UniqueConstraint("region", "country", name="uq_region_country"),)


class DimChannel(Base):
    __tablename__ = "dim_channel"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel: Mapped[str] = mapped_column(String(120), unique=True, index=True)


class DimRep(Base):
    __tablename__ = "dim_sales_rep"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rep_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)


# ---------------- Fact ----------------


class FactSale(Base):
    __tablename__ = "fact_sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(String(36), index=True)
    order_id: Mapped[str] = mapped_column(String(80), index=True)
    line_num: Mapped[int] = mapped_column(Integer, default=1)
    date_key: Mapped[int] = mapped_column(Integer, ForeignKey("dim_date.date_key"), index=True)
    customer_key: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("dim_customer.id"), nullable=True, index=True
    )
    product_key: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("dim_product.id"), nullable=True, index=True
    )
    region_key: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("dim_region.id"), nullable=True, index=True
    )
    channel_key: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("dim_channel.id"), nullable=True, index=True
    )
    rep_key: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("dim_sales_rep.id"), nullable=True
    )

    quantity: Mapped[float] = mapped_column(Numeric(12, 2))
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    discount: Mapped[float] = mapped_column(Numeric(12, 4), default=0)  # 0-1 fraction
    cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    shipping_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    revenue: Mapped[float] = mapped_column(Numeric(12, 2), index=True)
    profit: Mapped[float] = mapped_column(Numeric(12, 2))

    payment_method: Mapped[str | None] = mapped_column(String(80), nullable=True)
    order_status: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("batch_id", "order_id", "line_num", name="uq_fact_batch_order_line"),
        Index("ix_fact_date_region", "date_key", "region_key"),
        Index("ix_fact_date_channel", "date_key", "channel_key"),
    )
