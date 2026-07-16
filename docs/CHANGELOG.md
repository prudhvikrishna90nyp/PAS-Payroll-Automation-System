# CHANGELOG

All notable changes to PAS — Payroll Automation System.

Format based on [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased]

### Planned
- React frontend (`frontend/`)
- REST API (`/api/v1/`)
- Role-based access control

---

## [0.3.0] — 2026-07-16

### Added
- Monorepo structure: `backend/` + `frontend/` (placeholder)
- Root-level documentation (`docs/`)
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
