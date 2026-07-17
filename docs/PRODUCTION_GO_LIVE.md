# PAS v1.0.0 — Controlled Production Go-Live Runbook

**Audience:** ops + payroll lead  
**Goal:** run PAS safely for **one company and one payroll month** in parallel with existing Excel/manual payroll.  
**Hard rule:** do **not** Approve/Lock a production run until employee-wise and statutory totals match Excel. Do not invent live opening balances or payroll figures.

Related:

- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) — install / migrate / smoke
- [PARALLEL_RUN_CHECKLIST.md](PARALLEL_RUN_CHECKLIST.md) — comparison worksheet
- [BACKUP_AND_RESTORE.md](BACKUP_AND_RESTORE.md) — backups
- [ROLES_AND_PERMISSIONS.md](ROLES_AND_PERMISSIONS.md) — groups
- [backend/docs/05_DEPLOYMENT.md](../backend/docs/05_DEPLOYMENT.md) — env and run modes

---

## 0. Scope for first live month

| Item | Controlled go-live choice |
|------|---------------------------|
| Companies | **One** real company (plus its client record) |
| Financial year | One FY matching your Excel books |
| Payroll period | **One** month only |
| Employees | Same headcount as Excel for that company/month |
| Finalize / Lock | Only after parallel-run sign-off |
| Fake / demo data | Never as production; use a separate demo DB if training |

---

## 1. Production server running

### Options (pick one)

| Mode | When to use | How |
|------|-------------|-----|
| **Docker Compose** (recommended) | Staging / first production host | `cd backend` → copy `.env.example` → `.env` → `docker compose up --build -d` → migrate + admin (below) |
| **Gunicorn + PostgreSQL** | Bare-metal / VM | Install `requirements/production.txt`, set `DJANGO_SETTINGS_MODULE=config.settings.production`, migrate, `collectstatic`, run `gunicorn config.wsgi:application --bind 0.0.0.0:8000` |
| **`runserver`** | Local/staging smoke only | `config.settings.development` — **not** for live payroll |

Docker services (`backend/docker-compose.yml`):

- `web` — Gunicorn on port **8000**, `config.settings.production`
- `db` — PostgreSQL 17 (`POSTGRES_DB=payroll`)

Local SQLite dev is unchanged: leave `DB_NAME` empty in `.env` and use `manage.py` defaults (`config.settings.development`).

### Quick verify

```bash
cd backend
# Docker
docker compose ps
curl -I http://127.0.0.1:8000/

# Or bare metal
export DJANGO_SETTINGS_MODULE=config.settings.production   # Windows: $env:DJANGO_SETTINGS_MODULE=...
python manage.py check
```

---

## 2. PostgreSQL configured

Production **must** use PostgreSQL (not SQLite).

Django reads **`DB_*`** from the environment (see `config/settings/base.py`):

| Variable | Role |
|----------|------|
| `DB_NAME` | If set → PostgreSQL; if empty → SQLite (dev only) |
| `DB_USER` | Default `postgres` |
| `DB_PASSWORD` | Required in prod |
| `DB_HOST` | Default `localhost` (`db` in Compose) |
| `DB_PORT` | Default `5432` |

Compose injects `DB_HOST=db` and matching credentials. Host Postgres container env uses `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` (Postgres image vars — not read by Django directly).

**Note:** PAS does not parse `DATABASE_URL` today. Map a URL into `DB_*` when provisioning. Example:

`postgresql://USER:PASS@HOST:5432/NAME` → `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` / `DB_NAME`.

### Migrate (Postgres)

```bash
cd backend
# Ensure .env has DB_NAME and credentials, then:
export DJANGO_SETTINGS_MODULE=config.settings.production
python manage.py migrate
python manage.py check
```

Docker:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py check
```

If Postgres is not installed on a laptop, migrate against local SQLite for verification only; use PostgreSQL before any real payroll data.

---

## 3. Environment variables and secrets

1. Copy `backend/.env.example` → `backend/.env`.
2. Set a strong unique `SECRET_KEY`.
3. Production: `DEBUG=False`, real `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SECURE_SSL_REDIRECT` as needed.
4. Fill `DB_*` for PostgreSQL.
5. Optional email stubs (`EMAIL_*`) — leave console/default until SMTP is ready.
6. Optional Docker admin bootstrap: `DJANGO_SUPERUSER_USERNAME` / `EMAIL` / `PASSWORD` (see §5).

**Never commit `.env` or real secrets.** Rotate any key that was committed or shared in chat.

---

## 4. Migrations completed

```bash
cd backend
python manage.py migrate
python manage.py makemigrations --check   # expect: No changes detected
python manage.py check                    # expect: 0 issues
```

Role groups seed on `post_migrate` (see §10). Statutory PF/ESI/PT/TDS **rule rows** are created lazily on first successful payroll calculation (or via compliance seed helpers in admin/tests).

---

## 5. Admin user

Interactive (any environment):

```bash
python manage.py createsuperuser
```

Non-interactive (Docker / CI), only when env vars are set:

```bash
python manage.py ensure_admin
```

Requires all of:

- `DJANGO_SUPERUSER_USERNAME`
- `DJANGO_SUPERUSER_EMAIL`
- `DJANGO_SUPERUSER_PASSWORD`

If the user already exists, the command is a no-op (does not reset password). Assign the user to the **Admin** or **Super Admin** group after first login ([ROLES_AND_PERMISSIONS.md](ROLES_AND_PERMISSIONS.md)).

---

## 6. Regular database backup

Before any parallel month and after every locked run:

1. Follow [BACKUP_AND_RESTORE.md](BACKUP_AND_RESTORE.md).
2. Use scripts:
   - `backend/scripts/backup_db.ps1` (Windows)
   - `backend/scripts/backup_db.sh` (Linux/macOS)
3. Schedule daily dumps (Task Scheduler / cron); retain ≥ 30 days off-host.
4. Complete a **restore dry-run** on staging once before go-live.

---

## 7. Company, branches, departments, designations

Setup order (UI + Django admin both exist):

1. **Client** — Clients app / `/clients/`
2. **Company** — `/company/companies/` (link to client; PF/ESI codes, TAN, etc. as needed)
3. **Branch(es)** — company branches
4. **Department(s)** and **Designation(s)** — company org masters (admin or company UI)
5. **Employees** — under the company; bank fields on employee master for later bank file work
6. **Shifts / holidays** (attendance) if used for the parallel month

Do **not** load fictional client data into the production database. Training/demo → separate DB or clearly tagged demo company name (e.g. `DEMO-*`) never used for bank payouts.

---

## 8. Salary components verified

For the go-live company:

1. Payroll → **Seed standard salary components** (`/payroll/components/seed/`) or create manually.
2. Confirm required codes exist and match your Excel structure (adjust formulas only after understanding engine behaviour).

| Code | Name | Role in engine |
|------|------|----------------|
| `BASIC`, `HRA`, `CONVEYANCE`, `SPECIAL`, … | Earnings | Structure / formula; PF/ESI flags matter |
| `EE_PF`, `EE_ESI`, `PT`, `TDS` | Structure placeholders | **Superseded** by statutory engine rows (`STAT_*`) on calculate |
| `LOAN`, `ADVANCE`, `OTHER_DED` | Fixed deductions | Enter recovery amounts on structure lines / assignment |
| `ER_PF`, `ER_ESI`, … | Employer | Structure placeholders; employer ESI also via `STAT_ER_ESI` |

Checklist:

- [ ] Standard components seeded for the company
- [ ] Salary **structure(s)** with correct lines and fixed amounts
- [ ] **Employee salary assignments** effective for the parallel month
- [ ] Gross / Basic logic matches Excel policy (document any intentional differences)

---

## 9. EPF, ESI, PT, TDS rules checked

Compliance hub: `/compliance/`  
Engines: `apps.compliance` (PF / ESI / PT / TDS). Rules resolve by **`effective_from` / `effective_to`** as of the payroll period end date.

| Statutory | Verify |
|-----------|--------|
| EPF | Active `PFRuleSet` covering period end; ceiling and rates match policy |
| ESI | Active `ESIRuleSet`; employee ESI profiles / wage ceiling as applicable |
| PT | `ProfessionalTaxRuleSet` + slabs for company **state**; employee PT profile |
| TDS | Tax regime / FY slabs; employee tax profile, declarations, proofs as needed |

After first successful **Calculate** on a run, confirm rule rows and result lines (`STAT_PF`, `STAT_ESI`, `STAT_PT`, `STAT_TDS`, employer lines). Compare rates to Excel for the same month.

---

## 10. User roles and permissions

Groups seed on migrate (`post_migrate` merge): **Super Admin**, **Admin**, **HR**, **Payroll**, **Viewer**.

See [ROLES_AND_PERMISSIONS.md](ROLES_AND_PERMISSIONS.md).

```bash
python manage.py shell -c "from django.contrib.auth.models import Group; print(list(Group.objects.values_list('name', flat=True)))"
```

Assign least-privilege roles for the parallel month (Payroll calculate/review; Admin approve/lock after sign-off).

---

## 11. Payslip format and payroll reports — smoke test

Automated:

```bash
cd backend
python manage.py test
```

Manual smoke (staging or empty prod before live data):

1. Create draft **PayrollPeriod** + **PayrollRun** for the test company/month.
2. **Calculate** → open employee result → **Payslip preview**.
3. Legacy payslips (if used): `/payroll/payslips/` → PDF (WeasyPrint; Windows needs GTK3 — see release notes).
4. Engine reports: `/payroll/reports/` — payroll register, earnings/deductions, **net salary register**.
5. Compliance exports: PF / ESI / PT / TDS / ECR / Form 16 preview as applicable.
6. **Bank advice / NEFT file:** not GA yet (post-1.0 backlog). For parallel run, export **Net Salary Register** and reconcile to Excel bank sheet using employee bank masters.

Do not Lock until parallel checklist is signed.

---

## 12. Opening balances, loans, advances

| Item | In PAS v1.0.0 | Guidance |
|------|---------------|----------|
| Opening YTD / TDS YTD | Tax / previous-employer and declaration screens under Compliance | Enter **real** figures from Excel only; leave blank if deferred |
| Loan recovery | Component `LOAN` (fixed deduction) on structure / assignment | No dedicated loan ledger module — track principal outside PAS if needed |
| Advance recovery | Component `ADVANCE` | Same as loans |
| Other deductions | `OTHER_DED` | Use for one-off recoveries |

Do **not** invent balances. If Excel has loan EMI for the month, set the matching fixed deduction amount for that month’s structure/assignment before Calculate.

---

## 13. Parallel-run process (one company, one month)

Use [PARALLEL_RUN_CHECKLIST.md](PARALLEL_RUN_CHECKLIST.md) as the working sheet.

### A. Prepare masters

1. Backup DB.
2. Create client → company → branch → dept → designation.
3. Import/enter employees (codes must match Excel for easy compare).
4. Seed salary components → structures → assignments.
5. Attendance / leave / OT for the month (lock attendance period when ready).
6. Enter loan/advance/other fixed recoveries and compliance profiles.
7. Create **PayrollPeriod** (open) and **PayrollRun** (draft).

### B. Draft payroll

1. **Calculate** the run (status may be Calculated / Incomplete — fix Incomplete employees).
2. Export or copy employee-wise: Gross, EPF, ESI, PT, TDS, LOAN, ADVANCE, Net, employer contrib.
3. Fill PAS vs Excel columns in the parallel checklist.
4. Correct masters / attendance / components; **recalculate** (do not Approve yet).
5. Repeat until employee-wise and company totals match within agreed tolerance (recommend ₹0.00 or documented rounding rule).

### C. Approve / lock (only when matched)

1. Sign-off on [PARALLEL_RUN_CHECKLIST.md](PARALLEL_RUN_CHECKLIST.md).
2. **Review** → **Approve** → **Lock**.
3. Generate payslips / register exports / statutory exports needed for filing.
4. Take a **post-finalization backup** and verify file size &gt; 0.

### D. After first locked month

- Keep Excel freeze for that month.
- Schedule the next month only after ops is comfortable.
- Reopen locked runs is **superuser-only** with mandatory remarks — avoid in production except incidents.

---

## 14. Go-live gate checklist (sign-off)

- [ ] Postgres + production settings + `DEBUG=False`
- [ ] Secrets only in `.env` / secret store
- [ ] `migrate` + `check` clean; role groups present
- [ ] Admin user + role assignments
- [ ] Backup job + restore dry-run done
- [ ] One company org tree complete
- [ ] Salary components / structures / assignments verified
- [ ] EPF/ESI/PT/TDS rules checked for period dates
- [ ] Parallel checklist signed (employee + totals)
- [ ] Payslip / net register / statutory export smoke OK
- [ ] Run **Locked** only after sign-off; backup taken

**Next step for the business user:** configure the single live company (client → org → employees → structures), pick the parallel payroll month, and start the draft calculate → Excel compare loop — do not lock until the checklist matches.
