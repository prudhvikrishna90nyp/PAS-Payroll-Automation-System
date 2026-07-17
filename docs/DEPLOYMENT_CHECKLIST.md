# PAS Production Deployment Checklist (v1.0.0)

Use with `backend/docs/05_DEPLOYMENT.md`. Complete every item before exposing PAS to production payroll data.

**Controlled first live month:** follow [PRODUCTION_GO_LIVE.md](PRODUCTION_GO_LIVE.md) and reconcile with Excel using [PARALLEL_RUN_CHECKLIST.md](PARALLEL_RUN_CHECKLIST.md). Do **not** Approve/Lock until totals match.

---

## 1. Pre-install

- [ ] Python 3.12+ (or Docker Compose stack)
- [ ] PostgreSQL 14+ (do **not** use SQLite in production)
- [ ] Strong unique `SECRET_KEY`
- [ ] `DEBUG=False`
- [ ] `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` set for the real domain
- [ ] TLS / HTTPS (`SECURE_SSL_REDIRECT=True` behind a terminating proxy if applicable)
- [ ] Media storage plan (`/media/` via nginx or object storage)

---

## 2. Install & migrate

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
source venv/bin/activate
pip install -r requirements/production.txt
cp .env.example .env   # edit production values (SECRET_KEY, DEBUG=False, ALLOWED_HOSTS, DB_*)
export DJANGO_SETTINGS_MODULE=config.settings.production
python manage.py migrate                 # apply schema + seed role groups (post_migrate)
python manage.py collectstatic --noinput
python manage.py createsuperuser
# Or non-interactive when DJANGO_SUPERUSER_* are set in .env:
# python manage.py ensure_admin
python manage.py check
python manage.py makemigrations --check  # expect: No changes detected
```

**Upgrade / redeploy migrate path:** take a DB backup → set production settings → `migrate` (usually no-op if already current) → `collectstatic` → restart the app. Verify with `check` and a locked-run smoke login.

Docker alternative:

```bash
cd backend
cp .env.example .env
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
# Or: docker compose exec web python manage.py ensure_admin
```

---

## 3. Seed groups & statutory rules

Role groups are seeded automatically on `migrate` / `post_migrate` from:

| App | What is seeded |
|-----|----------------|
| `employee` | Employee document / structure perms (merge) |
| `attendance` | Attendance masters / period reopen |
| `payroll` | Salary masters, periods, runs, payslips, audit view |
| `compliance` | PF/ESI/PT/TDS **export** permissions |
| `company` / `clients` | Company, branch, dept, designation, client CRUD |

Assign users to groups: **Super Admin**, **Admin**, **HR**, **Payroll**, **Viewer**.

Statutory PF/ESI/PT/TDS **rule rows** are created/updated when payroll calculation runs (lazy seed). After first successful calc on a company, verify Compliance hub masters.

Optional UI: Payroll → Seed standard salary components.

---

## 4. Smoke verification

- [ ] Login as Admin; open dashboard
- [ ] Create/view Client → Company → Branch
- [ ] Create employee + salary assignment
- [ ] Open payroll period → create run → Calculate
- [ ] Confirm EPF/ESI/PT/TDS components as applicable
- [ ] Review → Approve → Lock; confirm audit trail on run detail
- [ ] Superuser reopen with remarks → recalculate succeeds
- [ ] Payslip list requires login; Viewer cannot archive company/client
- [ ] Export one compliance register (PF or TDS)

```bash
python manage.py test
```

---

## 5. Backup before go-live

- [ ] Configure scheduled DB backups per [BACKUP_AND_RESTORE.md](BACKUP_AND_RESTORE.md)
- [ ] Run `backend/scripts/backup_db.ps1` (Windows) or `backend/scripts/backup_db.sh` (Linux/macOS)
- [ ] Take a verified restore dry-run on a staging host
- [ ] Document restore RTO/RPO for the ops team

---

## 6. Cutover (controlled parallel run)

Full runbook: [PRODUCTION_GO_LIVE.md](PRODUCTION_GO_LIVE.md). Worksheet: [PARALLEL_RUN_CHECKLIST.md](PARALLEL_RUN_CHECKLIST.md).

- [ ] Start with **one company** and **one payroll month** only
- [ ] Freeze parallel spreadsheet payroll for that month (Excel remains source of truth until match)
- [ ] Import/verify employee masters and bank details (no fictional live data)
- [ ] Draft calculate → reconcile Gross / EPF / ESI / PT / TDS / loans / net / employer contrib
- [ ] Lock first production run **only** after [PARALLEL_RUN_CHECKLIST.md](PARALLEL_RUN_CHECKLIST.md) sign-off
- [ ] Backup immediately after lock
