# Parallel Run Checklist — PAS vs Excel

**PAS version:** v1.0.0  
**Company:** _______________________  
**Client:** _______________________  
**Payroll period (MM/YYYY):** ________  
**Financial year:** ________  
**Prepared by:** ________ **Date:** ________  
**Reviewed by:** ________ **Date:** ________  

**Rule:** Do not Approve/Lock the PAS payroll run until Sections B and C match within the agreed tolerance. Do not invent figures — copy from Excel/manual payroll and from PAS draft results only.

**Agreed tolerance:** ₹ ________ (recommend `0.00` or documented rounding)

---

## A. Preconditions

| # | Check | Done |
|---|--------|------|
| A1 | Production/staging DB backed up | [ ] |
| A2 | One company masters complete (branch, dept, designation) | [ ] |
| A3 | Employee headcount matches Excel for this month | [ ] |
| A4 | Salary structures / assignments effective for period | [ ] |
| A5 | Attendance / LOP / OT entered (or confirmed N/A) | [ ] |
| A6 | Loan / advance / other fixed recoveries entered (real amounts only) | [ ] |
| A7 | EPF / ESI / PT / TDS profiles & rules checked for period end date | [ ] |
| A8 | PAS run calculated (Draft/Calculated); **not** Locked | [ ] |

---

## B. Employee-wise comparison

Copy rows from PAS **Net Salary Register** / run detail and from Excel. Add rows as needed. Mark **Match** = Y only if all compared columns are within tolerance.

| Emp code | Emp name | Gross PAS | Gross Excel | EPF EE PAS | EPF EE Excel | ESI EE PAS | ESI EE Excel | PT PAS | PT Excel | TDS PAS | TDS Excel | Loan PAS | Loan Excel | Adv PAS | Adv Excel | Net PAS | Net Excel | ER PF/ESI PAS | ER Excel | Match (Y/N) | Notes |
|----------|----------|-----------|-------------|------------|--------------|------------|--------------|--------|----------|---------|-----------|----------|------------|---------|-----------|---------|-----------|---------------|----------|-------------|-------|
| | | | | | | | | | | | | | | | | | | | | | |
| | | | | | | | | | | | | | | | | | | | | | |
| | | | | | | | | | | | | | | | | | | | | | |
| | | | | | | | | | | | | | | | | | | | | | |
| | | | | | | | | | | | | | | | | | | | | | |

_Attach exported Excel sheets if easier; keep this table as the sign-off summary or paste totals only._

**Employees with Match = N:** list codes and root cause (master / attendance / component / statutory):

1. _______________________________________________
2. _______________________________________________
3. _______________________________________________

After fixes: recalculate PAS → refresh columns → clear Match = N rows.

---

## C. Company totals comparison

| Total | PAS | Excel | Diff (PAS − Excel) | Within tolerance? |
|-------|-----|-------|--------------------|-------------------|
| Headcount paid | | | | [ ] |
| Gross earnings | | | | [ ] |
| Employee EPF | | | | [ ] |
| Employer EPF / EPS / EDLI (as used) | | | | [ ] |
| Employee ESI | | | | [ ] |
| Employer ESI | | | | [ ] |
| Professional tax | | | | [ ] |
| TDS | | | | [ ] |
| Loan recoveries | | | | [ ] |
| Advance recoveries | | | | [ ] |
| Other deductions | | | | [ ] |
| **Net pay** | | | | [ ] |
| Employer contributions (CTC view, if used) | | | | [ ] |

---

## D. Statutory / report spot checks

| Check | PAS source | Excel / filing source | OK |
|-------|------------|----------------------|----|
| PF wages / EE+ER sample (3 employees) | Compliance PF export / run components | PF worksheet | [ ] |
| ESI wages / contrib sample | ESI export | ESI worksheet | [ ] |
| PT challan total | PT export | PT worksheet | [ ] |
| TDS month total | TDS register | TDS worksheet | [ ] |
| Payslip preview sample (2 employees) | Run payslip preview / PDF | Payslip Excel | [ ] |
| Net register vs bank sheet | `/payroll/reports/engine/net-salary-register/` | Bank payment sheet | [ ] |

Note: dedicated bank advice / NEFT export is post-1.0; use net register + employee bank fields for parallel bank compare.

---

## E. Sign-off (required before Approve / Lock)

| Role | Name | Signature / date |
|------|------|------------------|
| Payroll preparer | | |
| Reviewer (HR/Finance) | | |
| Approver (Admin) | | |

- [ ] Section B: all employees Match = Y (or documented exceptions attached)
- [ ] Section C: all totals within tolerance
- [ ] Section D: spot checks OK
- [ ] PAS run may proceed: **Review → Approve → Lock**
- [ ] Post-lock database backup taken ([BACKUP_AND_RESTORE.md](BACKUP_AND_RESTORE.md))

**Exceptions attached:** [ ] Yes (describe) __________________  [ ] None

---

## F. After lock

| Step | Done |
|------|------|
| Generate / archive payslips needed for distribution | [ ] |
| Export statutory files required for this month | [ ] |
| Store parallel checklist + exports with period folder | [ ] |
| Backup verified (size &gt; 0) | [ ] |

Return to [PRODUCTION_GO_LIVE.md](PRODUCTION_GO_LIVE.md) for the full runbook.
