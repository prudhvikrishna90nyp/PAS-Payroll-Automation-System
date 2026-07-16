# PayrollAutomation — Roadmap

## Phase 1 — Foundation (Complete)

- [x] Django project setup with modular apps
- [x] Company master (statutory registrations, contact, logo, bank details)
- [x] Employee and department management
- [x] Pay period and payslip generation
- [x] Attendance records
- [x] Shared Bootstrap layout (sidebar, navbar, dashboard)
- [x] Admin panel for all master data
- [x] Excel export for payslips
- [x] PDF payslip generation (WeasyPrint)

## Phase 2 — Core Payroll (In Progress)

- [ ] Company setup UI (outside admin)
- [ ] Employee CRUD from web interface
- [ ] Attendance marking from web interface
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

- [ ] Multi-company support
- [ ] Leave management integration
- [ ] Salary revision history
- [ ] Loan and advance deductions
- [ ] REST API for third-party integrations
- [ ] Audit log for payroll changes

## Phase 5 — Production & Scale

- [ ] PostgreSQL as default production database
- [ ] Celery for async payslip generation
- [ ] Automated backups
- [ ] CI/CD pipeline
- [ ] Docker deployment
