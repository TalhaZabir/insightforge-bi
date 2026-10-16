"""Analytics + insights + export tests on a hand-computed mini dataset (Part 5)."""
from __future__ import annotations

import io
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

# P1 (prev): 2024-01-01..2024-01-10 | P2 (cur): 2024-01-11..2024-01-20
# P1: O-1 rev200/profit75, O-2 rev80/profit-5  -> rev280 profit70 orders2 units3
# P2: O-3 rev100/profit40, O-4 rev135/profit40, O-6 rev100/profit40 -> rev335 profit120 orders3 units5
#     O-5 cancelled (excluded by default)


def _d(db, iso):
    d = date.fromisoformat(iso)
    key = int(iso.replace("-", ""))
    row = DimDate(date_key=key, date=d, year=d.year, quarter=1, month=d.month,
                  month_name="January", day=d.day, weekday=d.weekday(),
                  weekday_name="x", is_weekend=False)
    db.add(row)
    db.flush()
    return key


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    eng = create_engine(f"sqlite:///{tmp_path}/a.db", connect_args={"check_same_thread": False})
    TS = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=eng)
    s = TS()
    s.add(User(email="a@t.io", hashed_password=hash_password("pw123456"), role="analyst"))
    ch = DimChannel(channel="Online")
    rg = DimRegion(region="West", country="USA")
    ca = DimCustomer(customer_id="C-A", customer_name="Ann", segment="Consumer")
    cb = DimCustomer(customer_id="C-B", customer_name="Bob", segment="SMB")
    cc = DimCustomer(customer_id="C-C", customer_name="Cat", segment="Enterprise")
    cd = DimCustomer(customer_id="C-D", customer_name="Dee", segment="Consumer")
    px = DimProduct(product_id="P-X", product_name="Xenon", category="Electronics",
                    subcategory="Audio")
    py = DimProduct(product_id="P-Y", product_name="Yarn", category="Apparel",
                    subcategory="Knitwear")
    s.add_all([ch, rg, ca, cb, cc, cd, px, py])
    s.flush()
    k = {d: _d(s, d) for d in ["2024-01-02", "2024-01-05", "2024-01-12",
                               "2024-01-15", "2024-01-18", "2024-01-19"]}

    def F(**kw):
        return FactSale(batch_id="b1", line_num=1, customer_key=kw.pop("ck", None),
                        product_key=kw.pop("pk", None), region_key=rg.id,
                        channel_key=ch.id, date_key=kw.pop("dk"), **kw)

    s.add_all([
        F(order_id="O-1", dk=k["2024-01-02"], ck=ca.id, pk=px.id, quantity=2,
          unit_price=100, discount=0, cost=60, shipping_cost=5, revenue=200, profit=75,
          order_status="Completed"),
        F(order_id="O-2", dk=k["2024-01-05"], ck=cc.id, pk=py.id, quantity=1,
          unit_price=100, discount=0.2, cost=85, shipping_cost=0, revenue=80, profit=-5,
          order_status="Completed"),
        F(order_id="O-3", dk=k["2024-01-12"], ck=cb.id, pk=px.id, quantity=1,
          unit_price=100, discount=0, cost=60, shipping_cost=0, revenue=100, profit=40,
          order_status="Completed"),
        F(order_id="O-4", dk=k["2024-01-15"], ck=cc.id, pk=px.id, quantity=3,
          unit_price=50, discount=0.1, cost=30, shipping_cost=5, revenue=135, profit=40,
          order_status="Completed"),
        F(order_id="O-5", dk=k["2024-01-18"], ck=ca.id, pk=py.id, quantity=1,
          unit_price=50, discount=0, cost=20, shipping_cost=0, revenue=50, profit=30,
          order_status="Cancelled"),
        F(order_id="O-6", dk=k["2024-01-19"], ck=cd.id, pk=px.id, quantity=1,
          unit_price=100, discount=0, cost=60, shipping_cost=0, revenue=100, profit=40,
          order_status="Completed"),
    ])
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
        tok = c.post("/auth/login",
                     json={"email": "a@t.io", "password": "pw123456"}).json()["access_token"]
        c.headers.update({"Authorization": f"Bearer {tok}"})
        yield c
    app.dependency_overrides.clear()


P2 = {"from": "2024-01-11", "to": "2024-01-20"}


def test_overview_kpis_and_growth(client: TestClient):
    r = client.get("/analytics/overview", params=P2).json()
    k = r["kpis"]
    assert k["revenue"]["value"] == pytest.approx(335.0)
    assert k["revenue"]["previous"] == pytest.approx(280.0)
    assert k["revenue"]["growth_pct"] == pytest.approx(19.643, abs=0.01)
    assert k["profit"]["value"] == pytest.approx(120.0)
    assert k["margin"]["value"] == pytest.approx(120 / 335)
    assert k["margin"]["delta_pp"] == pytest.approx((120 / 335 - 70 / 280) * 100)
    assert k["orders"]["value"] == 3  # cancelled excluded
    assert k["aov"]["value"] == pytest.approx(335 / 3)
    # C-A's only P2 order is cancelled, so it confers no active-customer status
    assert r["customers"] == {"total": 3, "new": 2, "returning": 1,
                              "repeat_rate": pytest.approx(33.333, abs=0.01),
                              "avg_revenue": pytest.approx(335 / 3)}


def test_breakdowns_and_table(client: TestClient):
    s = client.get("/analytics/sales", params=P2).json()
    assert s["trend"]["grain"] == "daily"
    assert len(s["trend"]["points"]) == 3  # 12th, 15th, 19th (cancelled excluded)
    assert s["by_channel"][0]["channel"] == "Online"
    assert s["by_region"][0]["region"] == "West"
    cats = {c["category"]: c for c in s["by_category"]}
    assert cats["Electronics"]["revenue"] == pytest.approx(335.0)
    assert "Apparel" not in cats  # only cancelled line in P2

    t = client.get("/analytics/sales/orders",
                   params={**P2, "page": 1, "page_size": 2, "sort": "revenue",
                           "direction": "desc"}).json()
    assert t["total"] == 3 and t["items"][0]["order_id"] == "O-4"

    p = client.get("/analytics/profitability", params=P2).json()
    assert p["kpis"]["profit"] == pytest.approx(120.0)
    assert {b["bucket"] for b in p["discount_buckets"]} == {"none", "low"}

    c = client.get("/analytics/customers", params=P2).json()
    assert c["metrics"]["new"] == 2 and c["top_customers"][0]["revenue"] > 0
    assert c["revenue_concentration_top3"] == pytest.approx(1.0)

    r = client.get("/analytics/regions", params=P2).json()
    assert r["ranking"][0]["rank"] == 1

    pr = client.get("/analytics/products", params=P2).json()
    assert pr["best_sellers"][0]["product_id"] == "P-X"
    assert any(x["product_id"] == "P-X" for x in pr["highest_profit"])


def test_insights_are_traceable(client: TestClient):
    r = client.get("/insights", params=P2).json()
    heads = [i["headline"] for i in r["insights"]]
    assert any("grew 19.6%" in h for h in heads)  # revenue trend
    assert any("expanded" in h for h in heads)  # margin
    assert any("Top 3 customers" in h for h in heads)  # concentration
    for i in r["insights"]:
        assert set(i) >= {"category", "severity", "headline", "explanation",
                          "metric", "action"}
        assert i["category"] in {"trend", "opportunity", "risk", "quality"}
        assert i["severity"] in {"positive", "neutral", "warning", "critical"}

    empty = client.get("/insights",
                       params={"from": "2030-01-01", "to": "2030-01-31"}).json()
    assert empty["insights"][0]["headline"].startswith("No orders")


def test_powerbi_export(client: TestClient):
    r = client.get("/exports/power-bi")
    assert r.status_code == 200
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert {"fact_sales.csv", "dim_customer.csv", "README.txt"} <= set(names)
