# Software Requirements Specification (SRS)

**Project:** PAS — Payroll Automation System  
**Version:** 1.0  
**Date:** July 2026

---

## 1. Introduction

### 1.1 Purpose

PAS is an enterprise payroll management system for Indian organizations. It automates employee payroll, statutory compliance data, attendance tracking, and reporting.

### 1.2 Scope

| In scope (Phase 1) | Out of scope (later phases) |
|--------------------|----------------------------|
| Client / Company / Branch master | React frontend SPA |
| Employee & department management | Full statutory filing (ECR, Form 16) |
| Pay period & payslip generation | Multi-tenant SaaS billing |
| Attendance records | Mobile app |
| PDF & Excel export | Biometric attendance integration |

---

## 2. User Roles

| Role | Description |
|------|-------------|
| **Admin** | Full system access, master data, user management |
| **HR** | Employee, attendance, payroll operations |
| **Employee** | View own payslip (planned) |

---

## 3. Functional Requirements

### 3.1 Client & Company Management

- **FR-01** System shall support Client → Company → Branch hierarchy
- **FR-02** CRUD for Client, Company, and Branch records
- **FR-03** Company shall store PAN, GSTIN, TAN, EPF Code, ESI Code, and logo
- **FR-04** PAN and GSTIN shall be validated on input
- **FR-05** Records shall support soft delete (not permanent removal)
- **FR-06** Lists shall support search, filters, and pagination

### 3.2 Employee Management

- **FR-10** Maintain employee master with department, salary, and bank details
- **FR-11** List active employees with department and designation

### 3.3 Attendance

- **FR-20** Record daily attendance (present, absent, leave, half day)
- **FR-21** Track check-in and check-out times

### 3.4 Payroll

- **FR-30** Define pay periods (monthly)
- **FR-31** Generate payslips for all active employees in a period
- **FR-32** Calculate earnings (Basic, HRA, Transport) and deductions (PF, TDS)
- **FR-33** Export payslips to PDF and Excel
- **FR-34** Payslip status: Draft / Finalized

### 3.5 Reports

- **FR-40** Summary counts for employees, departments, and payslips
- **FR-41** Export payslip data to Excel

### 3.6 Authentication

- **FR-50** Login required for dashboard
- **FR-51** Django admin for master data management

---

## 4. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-01 | Web-based, responsive Bootstrap UI |
| NFR-02 | SQLite for development, PostgreSQL for production |
| NFR-03 | Timezone: Asia/Kolkata |
| NFR-04 | Docker deployment support |
| NFR-05 | Page load under 3 seconds for lists up to 1000 records |

---

## 5. Technology Stack

| Layer | Technology |
|-------|------------|
| Backend | Django 6, Python 3.12+ |
| Database | SQLite / PostgreSQL |
| Templates | Django Templates + Bootstrap 5 |
| PDF | WeasyPrint |
| Excel | openpyxl |
| Frontend (Phase 2) | React + TypeScript |

---

## 6. Assumptions & Constraints

- Single organization deployment per instance (multi-tenant planned Phase 4)
- Statutory calculation rules are simplified placeholders until Phase 3
- GSTIN/PAN validation is format-only, not live government API verification
