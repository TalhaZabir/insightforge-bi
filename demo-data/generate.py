"""InsightForge BI demo-data generator.

Deterministic (seeded) realistic retail sales data for 24 months plus
~2% intentionally imperfect rows to exercise validation.

Usage (from repo root):
    python demo-data/generate.py [--rows 12000] [--out demo-data]

Outputs:
    insightforge_demo_sales.csv
    insightforge_demo_sales.xlsx  (sheets: Sales, README)
"""
from __future__ import annotations

import argparse
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

SEED = 42

FIRST = ["Ava","Liam","Maya","Noah","Sofia","Ethan","Priya","Lucas","Amara","Owen",
         "Zoe","Mason","Nora","Eli","Ivy","Caleb","Ruby","Jonas","Elena","Marcus",
         "Tessa","Omar","Lena","Victor","Hana","Diego","Clara","Sam","Nadia","Peter",
         "Grace","Tom","Aisha","Leo","Mira","Felix","Dana","Ruth","Ken","Alba"]
LAST = ["Carter","Nguyen","Patel","Garcia","Kim","Johnson","Weber","Silva","Haddad","Okafor",
        "Bennett","Rossi","Khan","Murphy","Tanaka","Ali","Brooks","Costa","Dube","Evans",
        "Fischer","Gupta","Hassan","Ivanov","Jensen","Kaur","Lopez","Meyer","Novak","Owens"]

BRANDS = ["Everline","Koda","Lumen","Atlas","Northpeak","Harbor","Solstice","Vantage"]
REPS = ["Sarah Mitchell","James Carter","Priya Sharma","Diego Fuentes",
        "Emily Chen","Marcus Webb","Aisha Bello","Tom Becker"]
CHANNELS = [("Online", 0.50), ("Retail Store", 0.35), ("Wholesale", 0.15)]
REGIONS = [(("West","USA"), 0.32),(("East","USA"), 0.30),(("South","USA"), 0.22),
           (("Midwest","USA"), 0.10),(("Ontario","Canada"), 0.06)]  # Midwest+Ontario intentionally weak
SEGMENTS = [("Consumer", 0.60), ("SMB", 0.25), ("Enterprise", 0.15)]
PAYMENTS = ["Credit Card","Credit Card","Credit Card","Debit Card","PayPal","Bank Transfer","Cash"]
STATUSES = [("Completed", 0.94), ("Pending", 0.03), ("Returned", 0.02), ("Cancelled", 0.01)]

# category -> list of (item, subcategory, price_lo, price_hi, margin)
CATALOG: dict[str, list[tuple[str, str, float, float, float]]] = {
    "Electronics": [
        ("Wireless Headphones", "Audio", 89, 299, 0.42), ("Bluetooth Speaker", "Audio", 49, 199, 0.45),
        ("Laptop 14in", "Computing", 799, 1499, 0.28), ("Mechanical Keyboard", "Accessories", 69, 159, 0.50),
        ("4K Monitor 27in", "Computing", 279, 549, 0.30), ("Smart Watch", "Wearables", 149, 399, 0.40),
        ("USB-C Dock", "Accessories", 79, 199, 0.52), ("Noise-Cancelling Earbuds", "Audio", 59, 199, 0.48),
    ],
    "Apparel": [
        ("Denim Jacket", "Outerwear", 59, 129, 0.55), ("Oxford Shirt", "Menswear", 39, 89, 0.58),
        ("Summer Dress", "Womenswear", 45, 120, 0.56), ("Running Shoes", "Footwear", 79, 179, 0.47),
        ("Wool Sweater", "Knitwear", 55, 130, 0.54), ("Chino Pants", "Menswear", 42, 95, 0.57),
        ("Leather Boots", "Footwear", 129, 289, 0.44), ("Windbreaker", "Outerwear", 65, 140, 0.53),
    ],
    "Home & Kitchen": [
        ("Chef Knife 8in", "Cookware", 49, 139, 0.55), ("Cast Iron Skillet", "Cookware", 39, 99, 0.52),
        ("Ceramic Vase Set", "Decor", 29, 89, 0.60), ("Air Fryer XL", "Appliances", 99, 229, 0.38),
        ("Linen Duvet Set", "Bedding", 79, 199, 0.53), ("Espresso Maker", "Appliances", 149, 399, 0.36),
        ("Cutting Board Set", "Cookware", 25, 69, 0.58), ("Table Lamp", "Decor", 35, 110, 0.57),
    ],
    "Sports": [
        ("Yoga Mat Pro", "Fitness", 29, 79, 0.58), ("Trail Backpack 30L", "Outdoor", 69, 159, 0.50),
        ("Dumbbell Pair 15lb", "Fitness", 49, 119, 0.46), ("Camping Tent 4P", "Outdoor", 149, 349, 0.40),
        ("Road Bike Helmet", "Cycling", 59, 149, 0.48), ("Insulated Bottle 1L", "Outdoor", 19, 45, 0.62),
        ("Resistance Band Set", "Fitness", 25, 65, 0.60), ("Hiking Boots", "Outdoor", 99, 229, 0.43),
    ],
    "Beauty": [
        ("Vitamin C Serum", "Skincare", 19, 55, 0.65), ("Moisturizer SPF30", "Skincare", 22, 60, 0.63),
        ("Hair Repair Mask", "Haircare", 15, 42, 0.62), ("Eau de Parfum 50ml", "Fragrance", 55, 140, 0.55),
        ("Shea Body Lotion", "Bodycare", 12, 32, 0.64), ("Clay Face Mask", "Skincare", 14, 36, 0.63),
        ("Argan Hair Oil", "Haircare", 16, 44, 0.61), ("Lip Care Trio", "Makeup", 12, 30, 0.66),
    ],
}

MONTH_SEASON = {1:0.85,2:0.80,3:0.90,4:0.95,5:1.00,6:1.05,7:1.05,8:1.00,9:0.95,10:1.00,11:1.35,12:1.50}
WEEKDAY_F = {0:0.95,1:0.95,2:1.0,3:1.0,4:1.05,5:1.25,6:1.15}


def weighted(rng: random.Random, choices: list[tuple[str, float]]) -> str:
    x = rng.random()
    acc = 0.0
    for val, w in choices:
        acc += w
        if x <= acc:
            return val
    return choices[-1][0]


def build_products() -> pd.DataFrame:
    rows = []
    pid = 1000
    for cat, items in CATALOG.items():
        for (item, sub, lo, hi, margin) in items:
            for brand in BRANDS[:3]:  # 8 items x 3 brands = 24 per category
                pid += 1
                rows.append({
                    "product_id": f"P-{pid}",
                    "product_name": f"{brand} {item}",
                    "category": cat, "subcategory": sub,
                    "base_price": round((lo + hi) / 2, 2),
                    "price_lo": lo, "price_hi": hi, "margin": margin,
                })
    df = pd.DataFrame(rows)
    assert len(df) == 120, len(df)
    # 3 high-revenue, low-margin heroes (cheap, huge volume via explicit boost)
    heroes = df.nlargest(3, "base_price").index
    df.loc[heroes, "margin"] = 0.08
    df.loc[heroes, "hero"] = True
    df["hero"] = df["hero"].fillna(False).infer_objects(copy=False).astype(bool)
    return df


def build_customers(rng: random.Random, n: int = 600) -> pd.DataFrame:
    combos = [(f, l) for f in FIRST for l in LAST]
    rng.shuffle(combos)
    rows = []
    for i in range(n):
        f, l = combos[i]
        seg = weighted(rng, SEGMENTS)
        rows.append({
            "customer_id": f"C-{1000+i}",
            "customer_name": f"{f} {l}" if seg != "Enterprise" else f"{l} & Sons Ltd.",
            "segment": seg,
            "weight": 3.0 if seg == "Enterprise" else (1.5 if seg == "SMB" else 1.0),
        })
    return pd.DataFrame(rows)


def generate(target_rows: int = 12000) -> pd.DataFrame:
    rng = random.Random(SEED)
    products = build_products()
    customers = build_customers(rng)
    cust_weights = customers["weight"].tolist()

    start, end = date(2024, 1, 1), date(2025, 12, 31)
    days = (end - start).days + 1
    per_day_base = target_rows / days

    recs: list[dict] = []
    order_seq = 0
    d = start
    while d <= end:
        trend = 1.0 if d.year == 2024 else 1.12  # 12% YoY growth story
        lam = per_day_base * MONTH_SEASON[d.month] * WEEKDAY_F[d.weekday()] * trend
        n_orders = max(0, int(rng.gauss(lam, lam ** 0.5)))
        for _ in range(n_orders):
            order_seq += 1
            oid = f"ORD-{d.year}-{order_seq:06d}"
            ci = rng.choices(range(len(customers)), weights=cust_weights, k=1)[0]
            cust = customers.iloc[ci]
            channel = weighted(rng, CHANNELS)
            (region, country) = weighted(rng, [((r, c), w) for (r, c), w in REGIONS])
            rep = rng.choice(REPS)
            status = weighted(rng, STATUSES)
            payment = rng.choice(PAYMENTS)
            n_lines = 1 if rng.random() < 0.85 else 2
            for _ in range(n_lines):
                pi = rng.randrange(len(products))
                p = products.iloc[pi]
                boost = 4.0 if p["hero"] else 1.0
                qty = rng.randint(5, 30) if channel == "Wholesale" else rng.randint(1, 5)
                if rng.random() < 0.15 * boost:
                    qty = min(qty * 2, 40)
                price = round(rng.uniform(p["price_lo"], p["price_hi"]), 2)
                discount = 0.0
                if rng.random() < (0.35 if d.month in (11, 12) else 0.15):
                    discount = rng.choice([0.05, 0.10, 0.15, 0.20])
                if channel == "Wholesale":
                    discount = max(discount, 0.10)
                cost = round(price * (1 - float(p["margin"])), 2)
                shipping = 0.0 if channel == "Wholesale" else round(rng.uniform(4.99, 12.99), 2)
                revenue = round(qty * price * (1 - discount), 2)
                profit = round(revenue - cost * qty - shipping, 2)
                recs.append({
                    "order_id": oid, "order_date": d.isoformat(),
                    "customer_id": cust["customer_id"], "customer_name": cust["customer_name"],
                    "customer_segment": cust["segment"],
                    "product_id": p["product_id"], "product_name": p["product_name"],
                    "category": p["category"], "subcategory": p["subcategory"],
                    "region": region, "country": country,
                    "sales_channel": channel, "sales_rep": rep,
                    "quantity": qty, "unit_price": price, "discount": discount,
                    "cost": cost, "shipping_cost": shipping,
                    "revenue": revenue, "profit": profit,
                    "payment_method": payment, "order_status": status,
                })
        d += timedelta(days=1)

    df = pd.DataFrame(recs)
    # Uniform sample across the full period (keeps all 24 months represented),
    # then append imperfect rows.
    n_clean = max(target_rows - 240, 1000)
    if len(df) > n_clean:
        df = df.sample(n=n_clean, random_state=SEED).reset_index(drop=True)
    df = _inject_imperfect_rows(df, rng)
    return df


def _inject_imperfect_rows(df: pd.DataFrame, rng: random.Random) -> pd.DataFrame:
    bad = df.sample(n=min(180, len(df) // 60), random_state=SEED).copy()
    mods = []
    for i, (_, row) in enumerate(bad.iterrows()):
        r = row.to_dict()
        kind = i % 14
        if kind == 0: r["order_id"] = ""
        elif kind == 1: r["order_date"] = "2024-13-45"
        elif kind == 2: r["quantity"] = 0
        elif kind == 3: r["quantity"] = -2
        elif kind == 4: r["discount"] = 1.5
        elif kind == 5: r["revenue"] = -50.0
        elif kind == 6: r["category"] = "Misc Stuff"
        elif kind == 7: r["region"] = "Atlantis"
        elif kind == 8: r["customer_id"] = ""
        elif kind == 9: r["product_id"] = ""
        elif kind == 10: r["quantity"] = 500  # outlier, still |z| > 3 at file scale
        elif kind == 11: r["revenue"] = 25000.0  # outlier, flagged not rejected
        elif kind == 12: r["unit_price"] = "$199.99"
        elif kind == 13: r["profit"] = 123456.0  # inconsistent profit
        mods.append(r)
    dupes = df.sample(n=60, random_state=7).to_dict("records")  # exact duplicates
    out = pd.concat([df, pd.DataFrame(mods), pd.DataFrame(dupes)], ignore_index=True)
    return out.sample(frac=1.0, random_state=SEED).reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=12000)
    ap.add_argument("--out", type=Path, default=Path("demo-data"))
    args = ap.parse_args()

    df = generate(args.rows)
    args.out.mkdir(parents=True, exist_ok=True)
    csv_path = args.out / "insightforge_demo_sales.csv"
    xlsx_path = args.out / "insightforge_demo_sales.xlsx"
    df.to_csv(csv_path, index=False)
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Sales", index=False)
        pd.DataFrame([{
            "about": "InsightForge BI demo dataset",
            "rows": len(df),
            "note": "Use the 'Sales' sheet for imports. ~2% rows are intentionally imperfect.",
        }]).to_excel(w, sheet_name="README", index=False)
    print(f"rows={len(df)} customers={df['customer_id'].nunique()} "
          f"products={df['product_id'].nunique()} "
          f"range={df['order_date'].min()}..{df['order_date'].max()}")
    print(f"wrote {csv_path} ({csv_path.stat().st_size/1e6:.1f} MB) and {xlsx_path.name}")


if __name__ == "__main__":
    main()
