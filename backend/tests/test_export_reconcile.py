"""Part 7: export bundle reconciliation."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.auth.security import hash_password
from app.db.session import Base, get_db
from app.main import app
from app.models.entities import (
    DimChannel,
    DimCustomer,
    DimDate,
    DimProduct,
    DimRegion,
    FactSale,
    User,
)


def _d(db, iso):
    d = date.fromisoformat(iso)
    key = int(iso.replace("-", ""))
    db.add(
        DimDate(
            date_key=key,
            date=d,
            year=d.year,
            quarter=1,
            month=d.month,
            month_name="January",
            day=d.day,
            weekday=d.weekday(),
            weekday_name="x",
            is_weekend=False,
        )
    )
    db.flush()
    return key


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    eng = create_engine(f"sqlite:///{tmp_path}/e.db", connect_args={"check_same_thread": False})
    TS = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=eng)
    s = TS()
    s.add(User(email="e@t.io", hashed_password=hash_password("pw123456"), role="analyst"))
    ch = DimChannel(channel="Online")
    rg = DimRegion(region="West", country="USA")
    ca = DimCustomer(customer_id="C-A", customer_name="Ann", segment="Consumer")
    px = DimProduct(product_id="P-X", product_name="X", category="Electronics", subcategory="Audio")
    s.add_all([ch, rg, ca, px])
    s.flush()
    k = _d(s, "2024-02-01")
    s.add(
        FactSale(
            batch_id="b1",
            order_id="O-1",
            line_num=1,
            date_key=k,
            customer_key=ca.id,
            product_key=px.id,
            region_key=rg.id,
            channel_key=ch.id,
            quantity=2,
            unit_price=100,
            discount=0,
            cost=60,
            shipping_cost=5,
            revenue=200,
            profit=75,
            order_status="Completed",
        )
    )
    s.add(
        FactSale(
            batch_id="b1",
            order_id="O-2",
            line_num=1,
            date_key=k,
            customer_key=ca.id,
            product_key=px.id,
            region_key=rg.id,
            channel_key=ch.id,
            quantity=1,
            unit_price=50,
            discount=0,
            cost=20,
            shipping_cost=0,
            revenue=50,
            profit=30,
            order_status="Completed",
        )
    )
    s.commit()
    s.close()

    def override():
        db = TS()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        tok = c.post("/auth/login", json={"email": "e@t.io", "password": "pw123456"}).json()[
            "access_token"
        ]
        c.headers.update({"Authorization": f"Bearer {tok}"})
        yield c
    app.dependency_overrides.clear()


def test_bundle_manifest_reconciles(client: TestClient):
    r = client.get("/exports/power-bi")
    assert r.status_code == 200
    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = set(zf.namelist())
    for need in {
        "fact_sales.csv",
        "dim_date.csv",
        "dim_customer.csv",
        "dim_product.csv",
        "dim_region.csv",
        "dim_channel.csv",
        "dim_sales_rep.csv",
        "README.txt",
        "data_dictionary.csv",
        "relationships.md",
        "measures.dax",
        "kpi_definitions.json",
        "manifest.json",
    }:
        assert need in names, f"missing {need}"
    manifest = json.loads(zf.read("manifest.json"))
    assert manifest["grain"] == "one row per order line"
    rows = list(csv.DictReader(io.StringIO(zf.read("fact_sales.csv").decode("utf-8"))))
    assert len(rows) == manifest["fact_rows"] == 2
    rev = round(sum(float(x["revenue"] or 0) for x in rows), 2)
    assert rev == pytest.approx(manifest["revenue_total"]) == pytest.approx(250.0)
    ov = client.get("/analytics/overview").json()
    assert ov["kpis"]["revenue"]["value"] == pytest.approx(manifest["revenue_total"])
    # filtered export respects status filter
    rf = client.get("/exports/power-bi", params={"status": "Completed"})
    assert rf.status_code == 200
