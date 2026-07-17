# PAS v1.0.0-rc1 — Release Notes

**Tag:** `v1.0.0-rc1`  
**Date:** 2026-07-17  
**Branch:** `release/v1.0.0-rc1`

This release candidate stabilizes PAS for production trial after foundation through Sprint 9.4 (TDS). Focus is critical bug fixes, permission hardening, regression coverage, and deployment/backup documentation — not major new features.

---

## Highlights since foundation

| Area | Status |
|------|--------|
| Client → Company → Branch / Dept / Designation | Complete |
| Employee masters, salary structures, assignments | Complete |
| Attendance periods, daily attendance, import/reports | Complete |
| Payroll periods, runs, formula engine, proration/LOP | Complete |
| Approval / lock / reopen workflow + payroll audit trail | Complete (RC reopen fix) |
| EPF / ESI / PT / TDS compliance engines + exports | Complete through Sprint 9.4 |
| Role groups (Super Admin, Admin, HR, Payroll, Viewer) | Seeded via `post_migrate` |
| Payslips (legacy + engine preview) / statutory reports | Available |

---

## RC1 fixes

1. **Legacy payslip endpoints required auth + permissions** — list/detail/PDF/Excel/generate were reachable without login.
2. **Company, client, and organisation CRUD permission gates** — mutate/archive now require model permissions (not login-only).
3. **Compliance export permissions seeded** into Admin / Payroll / HR / Super Admin groups.
4. **Employee role seed merges** permissions instead of replacing group membership (no longer wipes payroll/attendance perms).
5. **Locked-run reopen → Calculated** so superuser reopen enables recalculation (was Approved, which blocked calc).
6. **User-facing ValidationError messages** formatted without Python list `repr` (e.g. `['…']`).
7. **Volume smoke test** — 20-employee `calculate_run` baseline (&lt; 60s on SQLite).

---

## Quality gate

```bash
cd backend
python manage.py check
python manage.py test
```

All checks and tests must pass before promoting beyond RC.

---

## Known risks before full v1.0.0

- React SPA / public REST API still planned (server-rendered UI is the v1 path).
- Bank advice / NEFT export and deeper remittance challans not complete.
- Statutory rule seeds run primarily on first payroll calculation (no dedicated management command yet).
- `apps.audit` package remains a stub; live audit is `PayrollAuditLog`.
- Large-volume N+1 on salary structure line loads may need tuning beyond ~hundreds of employees.
- Email payslips and automated backups are not productized (manual backup documented).
- WeasyPrint PDF on Windows needs GTK3 runtime.

---

## Upgrade path

See [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) and [BACKUP_AND_RESTORE.md](BACKUP_AND_RESTORE.md).
