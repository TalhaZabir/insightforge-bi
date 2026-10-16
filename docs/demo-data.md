# Demo data

Generator: `demo-data/generate.py` (seeded, deterministic — same output every run).

```powershell
python demo-data/generate.py --rows 12000 --out demo-data
```

What it builds: 24 months (2024-01-01…2025-12-31), ~12k rows, 600 customers
(Consumer/SMB/Enterprise), 120 products across Electronics / Apparel /
Home & Kitchen / Sports / Beauty, 5 regions (weak Midwest + Ontario on
purpose), 3 channels, 8 reps, November–December seasonality, +12% YoY trend,
3 high-revenue/low-margin hero SKUs, ~2% imperfect rows (bad dates, bad
quantities, percent-scale discounts, unknown vocab, blanks, exact
duplicates, z-outliers sized to flag without wrecking totals).

Outputs: `insightforge_demo_sales.csv` + `insightforge_demo_sales.xlsx`
(sheets `Sales` + `README`, so sheet selection is exercisable).

Seeds: `cd backend && python -m app.seeds.run` — demo users + 2023–2026
calendar; idempotent (safe to re-run).
