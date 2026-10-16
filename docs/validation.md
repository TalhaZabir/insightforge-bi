# Validation rules & cleaning

## Errors (row rejected, kept in `rejected_records` + rejection CSV)

- blank `order_id`; blank/unparseable/out-of-bounds `order_date`
  (bounds 2000-01-01 … today+365d); blank/non-numeric/`<= 0` quantity
- negative revenue / price / cost / shipping; non-numeric money fields
- `discount` outside 0–100 (% scale); revenue **and** unit price both
  missing (nothing to derive from)

## Warnings (row kept, flagged)

- blank `customer_id` / `product_id`; unknown category / region / status
  (after alias normalization); `profit` inconsistent with
  `revenue − cost×qty − shipping` (recomputed); duplicate `order_id` with
  different content; outlier quantity / revenue (|z| > 3, n ≥ 10)

## Cleaning (all logged in `transformations`, examples kept)

trim → normalize category/region/status vocab → ISO dates → strip
`$ , %` → percent-scale discounts ÷100 → blank cost/shipping → 0 →
derive `revenue = qty × price × (1−discount)` →
derive/repair `profit = revenue − cost×qty − shipping` →
drop exact duplicates (keep first).

Rejected + duplicate counts always reconcile:
`detected = valid + rejected + duplicates`. Nothing is silently deleted.
