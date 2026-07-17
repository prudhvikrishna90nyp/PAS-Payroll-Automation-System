# DATABASE

## Overview

- **ORM:** Django 6
- **Development:** SQLite (`backend/db.sqlite3`)
- **Production:** PostgreSQL 17 (set `DB_NAME` in `.env`)
- **Base model:** All business models inherit `BaseModel` (`created_at`, `updated_at`, `is_active`)
- Legacy table names `employees_*` preserved via `db_table`

---

## Build Order

```
Client → Company → Branch → Department → Designation → Employee
  → Attendance → Salary Structure → Payroll → Payslip
```

---

## Entity Hierarchy

```
Client
  └── Company
        └── Branch

Department ──< Employee ──< Attendance
Company ──< Shift / Holiday / AttendancePeriod
Employee ──< WeeklyOff / ShiftAssignment / AttendanceMonthlySummary
                  │
                  └──< Payslip >── PayPeriod
                           │
                           └──< PayslipItem
```

---

## clients app

### Client (`clients_client`)

| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | PK |
| name | CharField(200) | |
| code | CharField(20) | Unique |
| contact_person | CharField(100) | |
| phone | CharField(20) | |
| email | EmailField | |
| address | TextField | |
| is_active | BooleanField | From `BaseModel` |
| is_deleted | BooleanField | Soft delete |
| deleted_at | DateTimeField | |
| created_at / updated_at | DateTimeField | From `BaseModel` |

---

## company app

| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | PK |
| client_id | FK → clients.Client | |
| company_name | CharField(200) | |
| trade_name | CharField(200) | |
| pan | CharField(10) | Validated |
| gstin | CharField(15) | Validated |
| tan | CharField(10) | |
| epf_code | CharField(50) | |
| esi_code | CharField(50) | |
| professional_tax_registration | CharField(50) | |
| labour_licence | CharField(50) | |
| address, state, district, pin_code | | Registered address |
| contact_person, phone, email | | |
| logo | ImageField | `media/company/logos/` |
| bank_details | TextField | |
| is_active, is_deleted, deleted_at | | Soft delete |

### Branch

| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | PK |
| company_id | FK → Company | |
| branch_name | CharField(200) | |
| code | CharField(20) | Unique per company |
| address, state, district, pin_code | | |
| contact_person, phone, email | | |
| is_head_office | BooleanField | |
| is_active, is_deleted, deleted_at | | Soft delete |

---

## employee app

### Department (`employees_department`)

| Column | Type |
|--------|------|
| id | BigAutoField PK |
| name | CharField(100) |
| code | CharField(20) unique |

### Employee (`employees_employee`)

| Column | Type |
|--------|------|
| id | BigAutoField PK |
| employee_id | CharField(20) unique |
| first_name, last_name | CharField(100) |
| email | EmailField |
| department_id | FK → Department |
| designation | CharField(100) |
| date_joined | DateField |
| basic_salary | Decimal(12,2) |
| bank_account, pan | CharField |
| is_active | BooleanField |

---

## payroll app

### PayPeriod (`employees_payperiod`)

| Column | Type |
|--------|------|
| year, month | PositiveIntegerField (unique together) |
| start_date, end_date | DateField |
| is_closed | BooleanField |

### Payslip (`employees_payslip`)

| Column | Type |
|--------|------|
| employee_id | FK → Employee |
| pay_period_id | FK → PayPeriod |
| basic_salary, gross_pay, total_deductions, net_pay | Decimal |
| status | draft / finalized |

### PayslipItem (`employees_payslipitem`)

| Column | Type |
|--------|------|
| payslip_id | FK → Payslip |
| item_type | earning / deduction |
| description | CharField(100) |
| amount | Decimal(12,2) |

---

## attendance app

### Shift / Holiday / AttendancePeriod
Company-scoped masters. Period status: `open` / `locked` / `processed` (unique company+month+year).

### Attendance (daily)
| Column | Type |
|--------|------|
| employee_id | FK → Employee |
| attendance_date | DateField |
| shift_id | FK → Shift (nullable) |
| status | P / A / H / WO / CL / SL / EL / LOP / HD / OD |
| check_in, check_out | TimeField |
| worked_hours, overtime_hours | Decimal |
| late_minutes, early_exit_minutes | Integer |
| remarks | TextField |
| approved | Boolean |

Unique: `(employee, attendance_date)`

### WeeklyOff / ShiftAssignment / AttendanceMonthlySummary
Employee-scoped offs/assignments; monthly summary feeds payroll (present/absent/leave/WO/holiday/HD/OT/late/LOP).
