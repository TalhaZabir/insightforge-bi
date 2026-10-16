"""Unit + API tests for the ingestion pipeline (Part 4)."""
from __future__ import annotations

import io
import time
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.auth.security import hash_password
from app.core.config import settings
from app.db.session import Base, SessionLocal, engine, get_db
from app.ingestion.cleaner import clean as run_clean
from app.ingestion.mapper import apply_mapping, check_mapping, suggest_mapping
from app.ingestion.parser import list_sheets, read_upload
from app.ingestion.validator import validate
from app.main import app
from app.models.entities import DimDate, User

FIX = Path(__file__).parent / "fixtures" / "small_sales.csv"
MAPPING = {
    "order_id": "order_id", "order_date": "order_date",
    "customer_id": "customer_id", "customer_name": "customer_name",
    "product_id": "product_id", "product_name": "product_name",
    "category": "category", "region": "region", "country": "country",
    "sales_channel": "sales_channel", "quantity": "quantity",
    "unit_price": "unit_price", "discount": "discount", "cost": "cost",
    "shipping_cost": "shipping_cost", "revenue": "revenue",
    "profit": "profit", "order_status": "order_status",
}


def mapped_frame() -> pd.DataFrame:
    df_raw, _, _ = read_upload(FIX)
    return apply_mapping(df_raw, MAPPING)


# ---------- parser ----------


def test_csv_parser_reads_fixture():
    df, sheets, enc = read_upload(FIX)
    assert sheets is None and enc is not None
    assert len(df) == 11 and "order_id" in df.columns


def test_csv_parser_cp1252(tmp_path):
    p = tmp_path / "enc.csv"
    p.write_bytes("order_id,order_date,quantity\nO-1,2024-01-01,1\nO-2,2024-01-02,caf\xe9\n".encode("cp1252"))
    df, _, enc = read_upload(p)
    assert enc == "cp1252" and len(df) == 2


def test_xlsx_sheet_selection(tmp_path):
    p = tmp_path / "w.xlsx"
    with pd.ExcelWriter(p) as w:
        pd.DataFrame({"a": [1]}).to_excel(w, sheet_name="Sales", index=False)
        pd.DataFrame({"b": [2]}).to_excel(w, sheet_name="Notes", index=False)
    assert list_sheets(p) == ["Sales", "Notes"]
    with pytest.raises(Exception):
        read_upload(p)
    df, sheets, _ = read_upload(p, sheet="Sales")
    assert list(df.columns) == ["a"] and sheets == ["Sales", "Notes"]


# ---------- mapper ----------


def test_mapper_suggests_aliases():
    m = suggest_mapping(["Order ID", "Transaction_Date", "QTY", "Sales", "client", "weird_col"])
    assert m["order_id"] == "Order ID"
    assert m["order_date"] == "Transaction_Date"
    assert m["quantity"] == "QTY"
    assert m["revenue"] == "Sales"
    assert m["customer_name"] == "client"
    assert "weird_col" not in m.values()


def test_mapper_requirement_checks():
    assert check_mapping({}, ["a"])  # missing everything
    ok = {"order_id": "a", "order_date": "b", "quantity": "c", "product_id": "d", "revenue": "e"}
    assert check_mapping(ok, ["a", "b", "c", "d", "e"]) == []
    alt = {"order_id": "a", "order_date": "b", "quantity": "c",
           "product_name": "d", "unit_price": "e"}
    assert check_mapping(alt, ["a", "b", "c", "d", "e"]) == []  # OR-groups satisfied


# ---------- validator + cleaner on hand-verified fixture ----------


def test_fixture_validation_counts():
    report = validate(mapped_frame())
    assert report.stats["total_rows"] == 11
    assert report.stats["rejected_rows"] == 4
    assert report.stats["duplicate_rows"] == 1
    assert report.stats["valid_rows"] == 6
    rules = {i["rule"] for i in report.issues if i["severity"] == "error"}
    assert {"blank_order_id", "invalid_date", "nonpositive_quantity",
            "discount_out_of_range"} <= rules
    assert any(i["rule"] == "profit_mismatch" and i["severity"] == "warning"
               for i in report.issues)
    assert any(i["rule"] == "unknown_category" for i in report.issues)
    assert any(i["rule"] == "missing_product_id" for i in report.issues)


def test_fixture_cleaning_math():
    df = mapped_frame()
    outcome = run_clean(df, validate(df))
    assert outcome.summary["rejected_rows"] == 4
    assert outcome.summary["duplicates_removed"] == 1
    assert outcome.summary["revenue_total"] == pytest.approx(569.97)
    profits = sorted(round(float(x), 2) for x in outcome.cleaned["profit"])
    assert profits == pytest.approx([5.0, 15.0, 20.0, 28.0, 55.0, 119.97])
    assert outcome.summary["rows_cleaned"] >= 4
    assert len(outcome.transformations) > 0 and len(outcome.examples) > 0
    # derived values land on the right rows
    by_order = {r["order_id"]: r for r in outcome.cleaned.to_dict("records")}
    assert float(by_order["O-1"]["revenue"]) == pytest.approx(180.0)
    assert float(by_order["O-1"]["profit"]) == pytest.approx(55.0)
    assert float(by_order["O-3"]["profit"]) == pytest.approx(15.0)
    assert float(by_order["O-10"]["revenue"]) == pytest.approx(179.97)


# ---------- full API lifecycle on an isolated DB ----------


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    test_engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    TestingSession = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=test_engine)

    s = TestingSession()
    s.add(User(email="analyst@t.io", hashed_password=hash_password("pw123456"),
               role="analyst"))
    s.add(User(email="viewer@t.io", hashed_password=hash_password("pw123456"),
               role="viewer"))
    s.add(DimDate(date_key=20240301, date=pd.to_datetime("2024-03-01").date(),
                  year=2024, quarter=1, month=3, month_name="March", day=1,
                  weekday=4, weekday_name="Friday", is_weekend=False))
    s.commit()
    s.close()

    def override():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    import app.api.uploads as uploads_mod

    monkeypatch.setattr(uploads_mod, "SessionFactory", TestingSession)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _login(c: TestClient) -> str:
    r = c.post("/auth/login", json={"email": "analyst@t.io", "password": "pw123456"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_upload_to_database_lifecycle(client: TestClient):
    token = _login(client)
    h = {"Authorization": f"Bearer {token}"}

    with open(FIX, "rb") as fh:
        r = client.post("/uploads", files={"file": ("small_sales.csv", fh, "text/csv")}, headers=h)
    assert r.status_code == 201, r.text
    file_id = r.json()["file_id"]

    # duplicate upload rejected
    with open(FIX, "rb") as fh:
        r = client.post("/uploads", files={"file": ("small_sales.csv", fh, "text/csv")}, headers=h)
    assert r.status_code == 409

    r = client.post(f"/uploads/{file_id}/preview", json={"limit": 5}, headers=h)
    assert r.status_code == 200 and r.json()["total_rows"] == 11
    assert r.json()["suggested_mapping"]["order_id"] == "order_id"

    r = client.post(f"/uploads/{file_id}/validate", json={"sheet": None, "mapping": MAPPING}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["summary"]["valid_rows"] == 6
    job_id = r.json()["job_id"]

    r = client.post(f"/uploads/{file_id}/clean", json={"job_id": job_id}, headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["summary"]["revenue_total"] == pytest.approx(569.97)

    r = client.post(f"/uploads/{file_id}/confirm", json={"job_id": job_id}, headers=h)
    assert r.status_code == 200
    for _ in range(100):  # background task completes during the test request
        s = client.get(f"/imports/{job_id}/status", headers=h).json()
        if s["status"] in ("confirmed", "failed"):
            break
        time.sleep(0.1)
    assert s["status"] == "confirmed", s
    assert s["stats"]["confirmation"]["confirmed_rows"] == 6
    assert s["stats"]["confirmation"]["revenue_total"] == pytest.approx(569.97)

    q = client.get(f"/data-quality/{job_id}", headers=h)
    assert q.status_code == 200
    assert q.json()["validation"]["total_rows"] == 11
    csv_dl = client.get(f"/data-quality/{job_id}/rejections.csv", headers=h)
    assert csv_dl.status_code == 200 and "blank_order_id" in csv_dl.text

    # viewer cannot upload (403) but can read quality report
    r = client.post("/auth/login", json={"email": "viewer@t.io", "password": "pw123456"})
    vh = {"Authorization": f"Bearer {r.json()['access_token']}"}
    with open(FIX, "rb") as fh:
        r = client.post("/uploads", files={"file": ("v.csv", fh, "text/csv")}, headers=vh)
    assert r.status_code == 403
    assert client.get(f"/data-quality/{job_id}", headers=vh).status_code == 200
