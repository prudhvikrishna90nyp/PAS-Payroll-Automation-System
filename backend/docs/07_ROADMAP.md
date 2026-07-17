# ROADMAP

## Phase 1 — Foundation (in progress)

- [x] Django monorepo (`backend/` + `frontend/` placeholder)
- [x] **Client Management module** (`apps.clients`) — first complete business module
- [x] Client → Company → Branch hierarchy with CRUD
- [x] Employee and department management
- [x] Pay period and payslip generation
- [x] Attendance records
- [x] Shared Bootstrap layout (sidebar, navbar, dashboard)
- [x] PAN / GSTIN validation, soft delete, pagination
- [x] Admin panel, Excel export, PDF payslips
- [x] Docker deployment files
- [x] `BaseModel` coding standard in `apps.common`
- [x] PostgreSQL 17 + DRF in tech stack

## Phase 2 — Core Payroll & React Frontend

- [ ] React SPA in `frontend/`
- [ ] REST API (`/api/v1/`)
- [ ] Employee CRUD from web UI
- [ ] Attendance marking from web UI
- [ ] Role-based access (HR, Admin, Employee)
- [ ] Payslip approval workflow (draft → finalized)
- [ ] Email payslips to employees

## Phase 3 — Statutory Compliance

- [ ] EPF / ESI calculation rules engine
- [ ] Professional tax by state
- [ ] TDS computation and Form 16
- [ ] ECR and ESI return file generation
- [ ] PF challan and remittance reports

## Phase 4 — Advanced Features

- [ ] Multi-company payroll runs
- [ ] Leave management
- [ ] Salary revision history
- [ ] Loan and advance deductions
- [ ] Audit log for payroll changes

## Phase 5 — Production & Scale

- [ ] Celery for async payslip generation
- [ ] Automated backups
- [ ] CI/CD pipeline
- [ ] Monitoring and alerting
