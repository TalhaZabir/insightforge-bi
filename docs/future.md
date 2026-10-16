# Future improvements

- Celery + Redis for large imports with progress percentages and retries.
- Refresh-token rotation + server-side denylist for instant revocation.
- Saved filter views, scheduled email/PDF executive briefs.
- Data-source connectors (Shopify, Stripe, NetSuite) behind the same
  validate → clean → confirm pipeline.
- Column-level lineage + mapping templates per supplier.
- Playwright end-to-end suite running against Compose (backend tests exist;
  frontend flow tests are manual today — see Part 10 test plan).
- Optional LLM insight narration behind an explicit, off-by-default setting
  with PII redaction (never ships data externally without configuration).
