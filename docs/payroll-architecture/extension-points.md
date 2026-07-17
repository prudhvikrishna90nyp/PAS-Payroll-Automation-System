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
| **Full TDS engine** | Replace `calculate_tds` stub; regime, declarations, Form 16 | **Planned (v0.8+)** |
| **Full PT engine** | Replace `calculate_professional_tax`; state slabs from company.state | **Planned (v0.8+)** |
| **PF / ESI compliance** | Wage ceilings, eligibility, ECR / returns from company codes | Stubs only; Phase 3 roadmap |
| **Bank advice** | Query finalized payslips + employee IFSC/account → NEFT Excel | Fields on employee; export **Planned** |
| **Attendance-linked pay** | Feed `AttendanceMonthlySummary.lop_days` / OT into calculator | Summaries **Implemented**; pay wiring **Planned** |

### Related

- [Calculation sequence](calculation-sequence.md)
- [Payroll lifecycle](lifecycle.md)
- [Roadmap](../../backend/docs/07_ROADMAP.md)
|
