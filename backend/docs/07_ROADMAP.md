# ROADMAP

## Phase 1 — Foundation (complete)

- [x] Django monorepo (`backend/` + `frontend/` placeholder)
- [x] **Client Management module** (`apps.clients`) — first complete business module
- [x] Client → Company → Branch hierarchy with CRUD
- [x] Employee and department management
- [x] Pay period and payslip generation
- [x] Attendance records
- [x] Attendance Management (shifts, holidays, periods, daily CRUD, import, reports)
- [x] Shared Bootstrap layout (sidebar, navbar, dashboard)
- [x] PAN / GSTIN validation, soft delete, pagination
- [x] Admin panel, Excel export, PDF payslips
- [x] Docker deployment files
- [x] `BaseModel` coding standard in `apps.common`
- [x] PostgreSQL 17 + DRF in tech stack

## Phase 2 — Core Payroll & React Frontend

- [ ] React SPA in `frontend/`
- [ ] REST API (`/api/v1/`)
- [x] Employee CRUD from web UI
- [x] Attendance marking from web UI
- [x] Role-based access (HR, Admin, Payroll, Viewer) — seeded groups + RC1 hardening
- [x] Payslip / payroll approval workflow (Draft → Calculated → Reviewed → Approved → Locked)
- [ ] Email payslips to employees

## Phase 3 — Statutory Compliance

- [x] EPF / ESI calculation rules engine (Sprint 9.1 / 9.2)
- [x] Professional tax by state (Sprint 9.3)
- [x] TDS computation and Form 16 prep (Sprint 9.4)
- [x] ECR and ESI return file generation
- [ ] PF challan and remittance reports (enhance)

## Phase 3b — v1.0 RC Stabilization

- [x] **v1.0.0-rc1** — permission hardening, reopen→recalc, release docs, regression suite (2026-07-17)
- [ ] Bank advice / NEFT export
- [ ] Production hardening beyond RC (volume N+1, automated backups)
- [ ] Full **v1.0.0** GA after RC soak

## Phase 4 — Advanced Features

- [ ] Multi-company payroll runs
- [ ] Leave management
- [ ] Salary revision history
- [ ] Loan and advance deductions
- [x] Audit log for payroll changes (`PayrollAuditLog`; `apps.audit` stub remains)

## Phase 5 — Production & Scale

- [ ] Celery for async payslip generation
- [ ] Automated backups
- [ ] CI/CD pipeline
- [ ] Monitoring and alerting
