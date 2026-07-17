# Extension points

> Part of [PAS Architecture](../ARCHITECTURE.md). Status tags: **Implemented** vs **Planned**.

Hooks and natural seams for upcoming features. Prefer new services under `apps/payroll/services/` (or dedicated apps) rather than hardcoding in views.

| Extension | Suggested seam | Status |
|-----------|----------------|--------|
| **Bonus / incentive** | `SalaryComponent` codes + formula refs (`BONUS`, `INCENTIVE` aliases already in formula engine) | Component-ready; run-time variable inputs **Planned** |
| **Arrears** | New earning items or adjustment payslip linked to prior `PayPeriod` | Alias `ARREARS` reserved; workflow **Planned** |
| **Loans / advances** | Deduction components or `Loan` model → installment `PayslipItem` | Roadmap Phase 4 |
| **Reimbursements** | Claim → approved amount → earning/non-taxable line | **Planned** |
| **Biometric / device import** | Attendance import pipeline (`import_export.py`) + shift resolution | Excel import **Implemented**; device APIs **Planned** |
| **Full TDS engine** | `apps.compliance` TDS service; replace `STAT_TDS` stub | **Planned (Sprint 9.4)** |
| **Full PT engine** | AP (and other state) slabs in `apps.compliance` | **Planned (Sprint 9.3)** |
| **ESI compliance** | Wage ceiling / eligibility in `apps.compliance` | **Planned (Sprint 9.2)** |
| **EPF compliance** | `PFRuleSet` versioning, `pf_engine`, ECR / PF registers | **Implemented (Sprint 9.1)** |
| **Bank advice** | Query finalized payslips + employee IFSC/account → NEFT Excel | Fields on employee; export **Planned** |
| **Attendance-linked pay** | Feed `AttendanceMonthlySummary.lop_days` / OT into calculator | Summaries **Implemented**; pay wiring **Implemented (Sprint 8.2)** |

### Statutory rule versioning (Sprint 9.1)

- `compliance.PFRuleSet` stores effective-dated EPF rates (ceiling, EE/ER/EPS/EDLI/admin/inspection).
- `PayrollRun.pf_rule_set` and `PayrollPFResult.rule_version` snapshot the rule used at calculation time so historical payroll stays accurate when rates change.
- Resolve rules by payroll period **end date** via `compliance.services.pf_rules.get_pf_rule_for_date`.

### Related

- [Calculation sequence](calculation-sequence.md)
- [Payroll lifecycle](lifecycle.md)
- [Roadmap](../../backend/docs/07_ROADMAP.md)
