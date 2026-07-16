# PayrollAutomation — Database Schema

## Overview

The application uses Django ORM. Default development database is SQLite (`db.sqlite3`). Production uses PostgreSQL when `DB_NAME` is set in `.env`.

Legacy table names (`employees_*`) are preserved via `db_table` for backward compatibility after the app split.

---

## company

### Company

| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | PK |
| company_name | CharField(200) | |
| trade_name | CharField(200) | Optional |
| pan | CharField(10) | |
| gstin | CharField(15) | |
| tan | CharField(10) | |
| epf_code | CharField(50) | EPF establishment code |
| esi_code | CharField(50) | ESI establishment code |
| professional_tax_registration | CharField(50) | |
| labour_licence | CharField(50) | |
| address | TextField | |
| state | CharField(100) | |
| district | CharField(100) | |
| pin_code | CharField(10) | |
| contact_person | CharField(100) | |
| phone | CharField(20) | |
| email | EmailField | |
| logo | ImageField | `media/company/logos/` |
| bank_details | TextField | |
| is_active | BooleanField | Default: true |
| created_at | DateTimeField | Auto |
| updated_at | DateTimeField | Auto |

---

## employee

### Department (`employees_department`)

| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | PK |
| name | CharField(100) | |
| code | CharField(20) | Unique |

### Employee (`employees_employee`)

| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | PK |
| employee_id | CharField(20) | Unique |
| first_name | CharField(100) | |
| last_name | CharField(100) | |
| email | EmailField | |
| department_id | FK → Department | Nullable |
| designation | CharField(100) | |
| date_joined | DateField | |
| basic_salary | Decimal(12,2) | |
| bank_account | CharField(50) | |
| pan | CharField(20) | |
| is_active | BooleanField | Default: true |
| created_at | DateTimeField | Auto |
| updated_at | DateTimeField | Auto |

---

## payroll

### PayPeriod (`employees_payperiod`)

| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | PK |
| year | PositiveIntegerField | |
| month | PositiveIntegerField | Unique with year |
| start_date | DateField | |
| end_date | DateField | |
| is_closed | BooleanField | Default: false |

### Payslip (`employees_payslip`)

| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | PK |
| employee_id | FK → Employee | |
| pay_period_id | FK → PayPeriod | |
| basic_salary | Decimal(12,2) | |
| gross_pay | Decimal(12,2) | |
| total_deductions | Decimal(12,2) | |
| net_pay | Decimal(12,2) | |
| status | CharField(20) | `draft` / `finalized` |
| generated_at | DateTimeField | Auto |

Unique: `(employee, pay_period)`

### PayslipItem (`employees_payslipitem`)

| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | PK |
| payslip_id | FK → Payslip | |
| item_type | CharField(20) | `earning` / `deduction` |
| description | CharField(100) | |
| amount | Decimal(12,2) | |

---

## attendance

### AttendanceRecord

| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | PK |
| employee_id | FK → Employee | |
| date | DateField | |
| status | CharField(20) | present / absent / leave / half_day |
| check_in | TimeField | Nullable |
| check_out | TimeField | Nullable |
| notes | TextField | |

Unique: `(employee, date)`

---

## Entity Relationships

```
Company (standalone master)

Department ──< Employee ──< AttendanceRecord
                  │
                  └──< Payslip >── PayPeriod
                           │
                           └──< PayslipItem
```
