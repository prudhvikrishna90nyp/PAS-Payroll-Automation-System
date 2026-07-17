# PAS v1.0.0 — Production Release Notes

**Tag:** `v1.0.0`  
**Date:** 2026-07-17  
**Branch:** `release/v1.0.0`  
**Promoted from:** `v1.0.0-rc1`

First production (GA) release of PAS — Payroll Automation System. Server-rendered Django UI with full payroll workflow and Indian statutory engines through TDS.

---

## Highlights

| Area | Status |
|------|--------|
| Client → Company → Branch / Dept / Designation | Complete |
| Employee masters, salary structures, assignments | Complete |
| Attendance periods, daily attendance, import/reports | Complete |
| Payroll periods, runs, formula engine, proration/LOP | Complete |
| Approval / lock / reopen workflow + payroll audit trail | Complete |
| EPF / ESI / PT / TDS compliance engines + exports | Complete (Sprint 9.1–9.4) |
| Role groups (Super Admin, Admin, HR, Payroll, Viewer) | Seeded via `post_migrate` |
| Payslips (legacy + engine preview) / statutory reports | Available |

---

## Included from RC1

1. Legacy payslip endpoints require auth + permissions.
2. Company, client, and organisation CRUD permission gates.
3. Compliance export permissions seeded into Admin / Payroll / HR / Super Admin.
4. Employee role seed merges permissions (does not wipe payroll/attendance grants).
5. Locked-run reopen → **Calculated** so recalculation works.
6. User-facing `ValidationError` messages without Python list `repr`.
7. Volume smoke test — 20-employee `calculate_run` baseline (&lt; 60s on SQLite).

No release-blocking defects found during GA promotion validation (docs-only finalize).

---

## Quality gate (validated for GA)

```bash
cd backend
python manage.py check          # 0 issues
python manage.py makemigrations --check   # no pending
python manage.py test           # full suite must pass
```

**Migrate path (fresh or upgrade):**

```bash
export DJANGO_SETTINGS_MODULE=config.settings.production   # or set in .env
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check
```

Role groups seed on `migrate` / `post_migrate`. Statutory PF/ESI/PT/TDS rule rows seed lazily on first successful payroll calculation.

---

## Production configuration (required)

| Setting | Guidance |
|---------|----------|
| `SECRET_KEY` | Strong unique value via env (never ship the insecure default) |
| `DEBUG` | `False` in production (`config.settings.production`) |
| `ALLOWED_HOSTS` | Real domain(s), comma-separated |
| `CSRF_TRUSTED_ORIGINS` | `https://…` origins as needed |
| Database | PostgreSQL — do not use SQLite for production payroll |

See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) and [BACKUP_AND_RESTORE.md](BACKUP_AND_RESTORE.md).

---

## Known post-1.0 backlog

- React SPA / public REST API (`/api/v1/`)
- Bank advice / NEFT export; deeper PF challan / remittance reports
- Dedicated management command for statutory rule seeds
- `apps.audit` package stub (live audit is `PayrollAuditLog`)
- Large-volume N+1 tuning beyond ~hundreds of employees
- Email payslips; automated backups (manual backup documented)
- WeasyPrint PDF on Windows needs GTK3 runtime
- Celery, CI/CD, monitoring

---

## Upgrade from RC1

Same schema path as RC1 tip on `main`. Apply `migrate` (expect no-op if already current), redeploy static, restart app workers. Take a DB backup before cutover per [BACKUP_AND_RESTORE.md](BACKUP_AND_RESTORE.md).
