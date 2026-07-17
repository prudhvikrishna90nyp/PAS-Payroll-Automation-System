# First Company Setup — This Machine (PAS v1.0.0)

**Prepared:** 2026-07-17  
**Branch used:** `docs/production-go-live`  
**Machine path:** `C:\Users\Prudhvi\PAS-Payroll-Automation-System`  
**Mode:** local staging against PostgreSQL (not a hardened production host)

Related runbooks: [PRODUCTION_GO_LIVE.md](PRODUCTION_GO_LIVE.md) · [PARALLEL_RUN_CHECKLIST.md](PARALLEL_RUN_CHECKLIST.md) · [BACKUP_AND_RESTORE.md](BACKUP_AND_RESTORE.md) · [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

**Hard rule:** keep payroll runs in **Draft / Calculated** until [PARALLEL_RUN_CHECKLIST.md](PARALLEL_RUN_CHECKLIST.md) matches Excel. Do **not** Approve/Lock until then.

---

## What was completed on this machine

| Step | Status | Notes |
|------|--------|-------|
| Inspect Docker / Postgres | Done | Docker Desktop installed but **engine blocked** (no WSL distro; `com.docker.service` Stopped). Native **PostgreSQL 17.10** used instead. |
| PostgreSQL service | Done | Windows service `postgresql-x64-17` **Running**, port `5432` |
| Database | Done | Database `payroll` on `localhost:5432` (user `postgres`) |
| `backend/.env` | Done | Copied from `.env.example` with generated `SECRET_KEY`; **not committed** |
| Python venv + deps | Done | `backend\venv` + `requirements\production.txt` |
| Migrations | Done | `python manage.py migrate` against Postgres — OK |
| `manage.py check` | Done | 0 issues; `makemigrations --check` — no changes |
| Role groups | Done | `Super Admin`, `Admin`, `HR`, `Payroll`, `Viewer` |
| Admin user | Done | Username `pas_admin` via `ensure_admin`; groups Super Admin + Admin |
| Live company / payroll data | **Not created** | Only migration seed client `DEFAULT` / `Default Client`. **No company rows.** Enter Deep Enterprises (or first client) in the UI. |

---

## Environment facts (this machine)

| Item | Value |
|------|--------|
| Postgres | `C:\Program Files\PostgreSQL\17\` |
| Service | `postgresql-x64-17` |
| DB | `payroll` @ `localhost:5432` |
| App `.env` | `C:\Users\Prudhvi\PAS-Payroll-Automation-System\backend\.env` |
| Settings for local staging | `DJANGO_SETTINGS_MODULE=config.settings.development` with `DEBUG=True` |
| Admin username | `pas_admin` |
| Admin password | See `DJANGO_SUPERUSER_PASSWORD` in `backend\.env` (change after first login) |

For a real production host later: set `DEBUG=False`, use `config.settings.production`, real `ALLOWED_HOSTS` / `CSRF_TRUSTED_ORIGINS`, HTTPS, and rotate secrets.

---

## How to run the app against this DB

PowerShell:

```powershell
cd C:\Users\Prudhvi\PAS-Payroll-Automation-System\backend

# Ensure Postgres is up
Get-Service postgresql-x64-17
# If stopped: Start-Service postgresql-x64-17   # may need elevated PowerShell

.\venv\Scripts\Activate.ps1
$env:DJANGO_SETTINGS_MODULE = "config.settings.development"
python manage.py runserver 127.0.0.1:8000
```

Then open:

- App: http://127.0.0.1:8000/
- Login: http://127.0.0.1:8000/accounts/login/ (or your accounts login URL)
- Django admin: http://127.0.0.1:8000/admin/

Verify DB still Postgres:

```powershell
python manage.py shell -c "from django.db import connection; print(connection.settings_dict['ENGINE'], connection.settings_dict['NAME'])"
```

Expect: `django.db.backends.postgresql` and `payroll`.

---

## Backup before entering live masters

```powershell
cd C:\Users\Prudhvi\PAS-Payroll-Automation-System
.\backend\scripts\backup_db.ps1
```

Ensure `pg_dump` is on PATH (or use full path `C:\Program Files\PostgreSQL\17\bin\pg_dump.exe`). See [BACKUP_AND_RESTORE.md](BACKUP_AND_RESTORE.md).

---

## Next UI steps — one company, one parallel month

Do **not** invent salaries, statutory codes, or lock a run. Enter **real** Excel-matching data only.

1. **Backup** (above).
2. **Client** — http://127.0.0.1:8000/clients/  
   - Create/update the real client (e.g. Deep Enterprises trading entity).  
   - You may leave or archive `Default Client` once the real client exists.
3. **Company** — http://127.0.0.1:8000/companies/add/  
   - Link to that client; fill PF/ESI/TAN/GSTIN etc. from real records only.
4. **Org masters** — branch(es), department(s), designation(s) for that company.
5. **Employees** — http://127.0.0.1:8000/employees/ — same headcount/codes as Excel for the parallel month.
6. **Salary components** — Payroll → seed standard components (`/payroll/components/seed/`), then structures + assignments effective for the month.
7. **Attendance / leave / OT** for the chosen month (if used).
8. **Compliance profiles** — `/compliance/` — EPF/ESI/PT/TDS as applicable (real figures only).
9. Create **one** PayrollPeriod + **one** PayrollRun → **Calculate** only (stay Draft/Calculated).
10. Fill [PARALLEL_RUN_CHECKLIST.md](PARALLEL_RUN_CHECKLIST.md) employee-wise and totals vs Excel; recalculate until matched.
11. **Only then:** Review → Approve → Lock → take a post-lock backup.

---

## Docker Compose note (blocked here)

`backend\docker-compose.yml` defines `web` + `db` (Postgres 17). On this machine Compose failed because:

1. No WSL distribution (`wsl -l` empty) — Docker Desktop Linux engine needs WSL2.
2. `com.docker.service` was Stopped (start may need elevation).

To use Compose later (optional):

```powershell
wsl --install Ubuntu
# reboot if prompted, then start Docker Desktop, then:
cd C:\Users\Prudhvi\PAS-Payroll-Automation-System\backend
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py ensure_admin
```

Until then, the native `postgresql-x64-17` + `runserver` path above is the working local staging setup.

---

## If Postgres service is missing on another PC

1. Install PostgreSQL 17 (winget: `winget install PostgreSQL.PostgreSQL.17`) **or** fix Docker/WSL and use Compose.
2. Create DB: `CREATE DATABASE payroll OWNER postgres;`
3. Copy `backend\.env.example` → `backend\.env`; set strong `SECRET_KEY` and `DB_*`.
4. `python manage.py migrate` → `ensure_admin` or `createsuperuser` → `check`.
5. Follow UI steps above; never Approve/Lock until the parallel checklist matches.
