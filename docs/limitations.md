# Known limitations (honest)

1. **No background-job broker.** Confirm runs in-process via
   `BackgroundTasks`. Fine for files up to ~100k rows; beyond that, add
   Celery/RQ + a results table (the job-status pattern already fits).
2. **Outlier detection is univariate z-score** (|z|>3). On skewed sales data
   it can flag legitimate wholesale orders — it warns, never rejects.
3. **Logout is client-side.** JWTs are stateless; server logout only audits.
   True revocation needs a denylist or short-lived + refresh rotation.
4. **SQLite vs Postgres.** Local fallback works, but `yield_per` streaming,
   concurrent writes and some locking behavior differ — run Compose before
   sharing results.
5. **XLS support is read-only** via openpyxl; legacy `.xls` formulas return
   cached values.
6. **Spaces in the Windows folder path** break `npm`/`.cmd` shims
   (documented workaround in `docs/setup.md`).
7. **No LLM narratives.** Insights are deterministic by design; optional LLM
   summarization is future work (disabled by default per spec).
