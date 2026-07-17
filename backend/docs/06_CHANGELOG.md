# CHANGELOG

All notable changes to PAS — Payroll Automation System.

Format based on [Keep a Changelog](https://keepachangelog.com/).

---

## [0.9.4] — 2026-07-17

### Added
- **Sprint 9.4 — TDS Compliance**
  - `FinancialYearTaxRule` / `TaxSlab` with seeded FY 2024-25 and 2025-26 OLD/NEW regime rates
  - Employee tax profile, declarations, investment proofs, previous employer income
  - TDS engine + annual projection; immutable `PayrollTDSResult` snapshots
  - TDS register / summary / missing-PAN reports; Form 16 preparation data (separate from calc)
  - Compliance hub pages under `/compliance/` for tax masters and Form 16 preview

### Notes
- Statutory stack complete through 9.4 (EPF + ESI + PT + TDS). **v1.0 RC stabilization** is next.

---

## [Unreleased]

### Added
- **Attendance Management (Sprint 6 / v0.6.0 candidate)** on `feature/attendance-management`
  - Shift, Holiday, AttendancePeriod, Attendance, WeeklyOff, ShiftAssignment, AttendanceMonthlySummary
  - Period open/lock/reopen/processed with edit enforcement
  - Daily attendance CRUD, filters, Excel import/export, Excel reports
  - Role-group permissions seeded via `AttendanceConfig` post_migrate

### Changed
- Replaced scaffold `AttendanceRecord` with daily `Attendance` (data migrated in `0002`)
- Renamed Django project package `payroll_project/` → `config/`
- Moved documentation from root `docs/` to `backend/docs/`
- Added `backend/media/` directory and root `LICENSE` (MIT)
- Numbered knowledge-base docs (`01_SRS.md` … `07_ROADMAP.md`)
- Expanded `backend/apps/` layout; added `common` app for shared mixins, validators, and utilities
- Introduced `BaseModel`; all business models inherit timestamp and active flags
- **Client Management module** — `Client` moved to `apps.clients` with full CRUD at `/clients/`
- Git workflow: `main` / `develop` / `feature/<module-name>`

### Planned
- React frontend (`frontend/`)
- REST API (`/api/v1/`)
- Tag `v0.6.0` after merge to main

---

## [0.3.0] — 2026-07-16

### Added
- Monorepo structure: `backend/` + `frontend/` (placeholder)
- Backend documentation (`backend/docs/`)
- Docker `Dockerfile` and `docker-compose.yml` in `backend/`
- Split requirements: `base.txt`, `dev.txt`, `production.txt`
- Dev scripts and smoke tests

### Changed
- Django apps moved to `backend/apps/`
- Project rebranded to **PAS — Payroll Automation System**

---

## [0.2.0] — 2026-07-16

### Added
- Client → Company → Branch hierarchy
- Client / Company / Branch CRUD with search, filters, pagination
- PAN and GSTIN validation
- Soft delete for master records
- Logo upload for companies
- Bootstrap shared layout (sidebar, navbar, footer)

---

## [0.1.0] — 2026-07-11

### Added
- Initial Django project with modular apps
- Employee, department, attendance, payroll modules
- Payslip generation with PDF and Excel export
- Company master (statutory fields)
- Django admin for all models
- SQLite development database with PostgreSQL support
