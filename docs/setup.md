# Local setup

## Option A — Docker (PostgreSQL, recommended)

```bash
cp .env.example .env
docker compose up --build
# frontend http://localhost:3000 · backend http://localhost:8000/docs
```

The backend container runs `alembic upgrade head` on start, then serves the API.

## Option B — Local, no Docker (SQLite fallback)

```powershell
Copy-Item .env.example .env
# backend
cd backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m alembic upgrade head
python -m app.seeds.run
python -m uvicorn app.main:app --reload --port 8000
# frontend (new shell)
cd frontend; npm install; npm run dev
```

Seeded logins: `admin@insightforge.io / Admin123!`,
`analyst@insightforge.io / Analyst123!`, `viewer@insightforge.io / Viewer123!`.

## Demo data

```powershell
python demo-data/generate.py --rows 12000 --out demo-data
```

Then sign in as analyst and import `demo-data/insightforge_demo_sales.csv`
through Data Imports (or the API — see `docs/api.md`).

> Windows note: the workspace folder contains spaces, which breaks
> `npm`/`tsc.cmd` wrappers. Prefer `node ".\node_modules\typescript\bin\tsc" --noEmit`
> for typechecks, or rename the folder to e.g. `insightforge-bi`.
