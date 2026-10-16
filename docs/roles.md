# User roles

| Capability | admin | analyst | viewer |
|---|---|---|---|
| View dashboards, insights | ✅ | ✅ | ✅ |
| Export Power BI bundle | ✅ | ✅ | ✅ (cleaned data only) |
| Upload / map / validate / clean / confirm | ✅ | ✅ | ❌ (403) |
| Discard uploads | ✅ | ❌ | ❌ |
| Manage users (`GET /auth/users`) | ✅ | ❌ | ❌ |
| View audit trail (DB `audit_logs`) | ✅ | ❌ | ❌ |

Enforcement: `require_role(...)` dependencies on every protected route —
verified by `tests/test_ingestion.py` (viewer upload → 403) and the
frontend hides Data Imports / Settings nav entries per role, with
`AuthGuard roles=[...]` as a second layer. Demo passwords are documented
in `docs/setup.md`; change them (or the seed) before any shared deployment.
