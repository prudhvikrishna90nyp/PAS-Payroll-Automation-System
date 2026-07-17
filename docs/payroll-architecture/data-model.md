# Data model

> Part of [PAS Architecture](../ARCHITECTURE.md). Status tags: **Implemented** vs **Planned**.

Canonical hierarchy and payroll entities. Table/column detail: [02_DATABASE.md](../../backend/docs/02_DATABASE.md).

```mermaid
erDiagram
  Client ||--o{ Company : owns
  Company ||--o{ Branch : has
  Company ||--o{ Department : has
  Company ||--o{ Designation : has
  Company ||--o{ Employee : employs
  Branch ||--o{ Employee : locates
  Department ||--o{ Employee : organises
  Designation ||--o{ Employee : titles

  Company ||--o{ Shift : defines
  Company ||--o{ Holiday : calendar
  Company ||--o{ AttendancePeriod : periods
  Employee ||--o{ Attendance : daily
  Shift ||--o{ Attendance : optional
  AttendancePeriod ||--o{ AttendanceMonthlySummary : aggregates
  Employee ||--o{ AttendanceMonthlySummary : monthly
  Employee ||--o{ WeeklyOff : offs
  Employee ||--o{ ShiftAssignment : roster

  Company ||--o{ SalaryComponent : masters
  Company ||--o{ SalaryStructure : templates
  SalaryStructure ||--o{ SalaryStructureLine : lines
  SalaryComponent ||--o{ SalaryStructureLine : used_by
  Employee ||--o{ EmployeeSalaryAssignment : assigned
  SalaryStructure ||--o{ EmployeeSalaryAssignment : applies

  PayPeriod ||--o{ Payslip : contains
  Employee ||--o{ Payslip : receives
  Payslip ||--o{ PayslipItem : lines

  Company ||--o{ PayrollPeriod : calendar
  PayrollPeriod ||--o{ PayrollRun : versions
  Company ||--o{ PayrollRun : processes
  PayrollRun ||--o{ PayrollResult : snapshots
  Employee ||--o{ PayrollResult : receives
  PayrollResult ||--o{ PayrollResultComponent : lines
  PayrollPeriod ||--o{ PayrollAuditLog : audits
  PayrollRun ||--o{ PayrollAuditLog : audits
```

### Org & people

| Entity | App | Role |
|--------|-----|------|
| `Client` | `clients` | Top-level tenant |
| `Company` | `company` | Legal employer; statutory codes (EPF/ESI/PT) |
| `Branch` / `Department` / `Designation` | `company` | Org structure |
| `Employee` | `employee` | Worker; bank (`bank_account_number`, `ifsc_code`), `basic_salary` (legacy sync) |

### Attendance (v0.6)

| Entity | Scope | Notes |
|--------|-------|-------|
| `Shift`, `Holiday`, `AttendancePeriod` | Company | Period unique on `(company, month, year)` |
| `Attendance` | Employee + date | Unique `(employee, attendance_date)`; `approved` bool |
| `WeeklyOff`, `ShiftAssignment` | Employee | Effective dating |
| `AttendanceMonthlySummary` | Employee + period | present / absent / leave / WO / holiday / HD / OT / late / LOP |

### Salary & payroll (v0.7)

| Entity | Scope | Notes |
|--------|-------|-------|
| `SalaryComponent` | Company | earning / deduction / employer_contribution; fixed / % / formula |
| `SalaryStructure` + `SalaryStructureLine` | Company | Line can override calc type, value, %, formula |
| `EmployeeSalaryAssignment` | Employee | `effective_from` / `effective_to`; closes prior open assignment |
| `PayPeriod` | Global (year+month) | **Legacy** `is_closed` flag; used by existing payslip generation |
| `Payslip` / `PayslipItem` | Employee + period | Status `draft` / `finalized`; unique `(employee, pay_period)` |

### Payroll engine (v0.8.1 foundation)

| Entity | Scope | Notes |
|--------|-------|-------|
| `PayrollPeriod` | Company + month + year | Open/Closed; unique `(company, month, year)`; overlapping date ranges rejected |
| `PayrollRun` | Period + company | `run_number` version; status Draft / Calculated / Reviewed / Approved / Locked (Draft used in 8.1) |
| `PayrollResult` | Run + employee | Attendance + pay snapshot fields; immutable intent when run Locked (enforced in 8.3) |
| `PayrollResultComponent` | Result | Component code/name/type/amount + `calculation_detail` JSON |
| `PayrollAuditLog` | Period and/or run | Action, user, timestamp, details JSON |

**Legacy:** `employee.SalaryStructure` (basic/HRA%/transport template) remains for older paths; Sprint 7 masters in `apps.payroll` are the component engine. Prefer `PayrollPeriod`/`PayrollRun` over `PayPeriod` going forward (**Implemented v0.8.1 foundation**).

### Related

- [Calculation sequence](calculation-sequence.md)
- [Locking rules](locking-rules.md)
|
