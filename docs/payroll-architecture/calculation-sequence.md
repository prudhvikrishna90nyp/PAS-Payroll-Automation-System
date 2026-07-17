# Calculation sequence

> Part of [PAS Architecture](../ARCHITECTURE.md). Status tags: **Implemented** vs **Planned**.

Service package: `apps/payroll/services/`.

## Payroll run engine (Sprint 8.2)

```mermaid
sequenceDiagram
  participant UI as Run detail UI
  participant Eng as payroll_engine.calculate_run
  participant Att as attendance_loader
  participant Sal as salary_loader
  participant Calc as calculator
  participant FE as formula_engine / salary_calculator
  participant Snap as snapshot

  UI->>Eng: Calculate / Recalculate (Draft|Calculated|Incomplete)
  Eng->>Eng: reject if Locked / Reviewed / Approved
  Eng->>Eng: clear prior PayrollResult rows (atomic)
  loop each eligible employee
    Eng->>Att: attendance snapshot
    Eng->>Sal: effective salary assignment
    Eng->>Calc: full-month components + proration
    Calc->>FE: fixed / % / formula (no eval)
    Calc-->>Eng: EmployeeCalcResult
    alt success
      Eng->>Snap: PayrollResult + Components
    else controlled failure
      Eng->>Eng: savepoint rollback; record error (no zero pay)
    end
  end
  Eng->>Eng: status Calculated or Incomplete
```

### Proration basis

| Symbol | Meaning |
|--------|---------|
| `calendar_days` | Inclusive days in `PayrollPeriod` (`end − start + 1`) |
| `eligible_days` | Days on rolls in the period (`max(join, start)` … `min(exit\|end, end)`) |
| `payable_days` (with summary) | `present_days + paid_leave + WO + holiday` (half-day already **0.5** in `present_days`); capped at `eligible_days` |
| `payable_days` (no summary) | `max(0, eligible_days − lop_days)` (`lop_days` defaults to 0) |
| `proration_factor` | `payable_days / calendar_days` |

Earnings and structure deductions are evaluated at full monthly rates, then multiplied by `proration_factor`. **EPF** is calculated via `apps.compliance` (Sprint 9.1) from PF-applicable earnings, ceiling, and the effective `PFRuleSet`. **ESI** is calculated via `apps.compliance` (Sprint 9.2) from ESI-applicable earnings, eligibility wage limit, contribution-period continuity, and the effective `ESIRuleSet`. **Professional Tax** is calculated via `apps.compliance` (Sprint 9.3) from employee work-state (`EmployeePTProfile`), effective state rule set + DB slabs (AP seeded; February special month). **TDS** is calculated via `apps.compliance` (Sprint 9.4) from employee tax profile / declaration regime, FY tax rules + DB slabs, annual income projection (YTD + remaining months + previous employer), rebate/surcharge/cess, and remaining liability ÷ months left.

### Run status after calculation

| Outcome | Status | Results |
|---------|--------|---------|
| All employees succeed | `Calculated` | One `PayrollResult` per employee (+ `PayrollPFResult` / `PayrollESIResult` / `PayrollPTResult`) |
| One or more fail | `Incomplete` | Successful employees kept; failures listed in `calculation_errors` (no fake zero salary) |
| Locked / Reviewed / Approved | Rejected | Unchanged |

Recalculation of unlocked runs replaces previous results inside `transaction.atomic`. The run stores `pf_rule_set`, `esi_rule_set`, and optional `pt_rule_set` resolved for the period end date.

---

## Legacy payslip path (v0.7)

```mermaid
sequenceDiagram
  participant View as Payslip / assignment UI
  participant Gen as payslip_generator
  participant Assign as EmployeeSalaryAssignment
  participant Calc as salary_calculator
  participant FE as formula_engine
  participant Stat as statutory stubs
  participant DB as Payslip + Items

  View->>Gen: generate_payslip(employee, pay_period)
  Gen->>Assign: resolve current assignment on period end_date
  alt assignment with structure lines
    Gen->>Calc: calculate_assignment_components
    Calc->>FE: topological order + evaluate_formula
    FE-->>Calc: component amounts
    Calc-->>Gen: earnings / deductions / gross
    opt no deduction lines
      Gen->>Stat: PF + TDS stubs
    end
  else no assignment
    Gen->>Gen: legacy basic + 40% HRA + transport
    Gen->>Stat: PF + TDS stubs
  end
  Gen->>DB: upsert Payslip (skip if finalized)
  Gen->>DB: replace PayslipItem rows
```

### Engines

| Module | Responsibility | Status |
|--------|----------------|--------|
| `formula_engine.py` | Safe AST eval (`+ - * / % **`); aliases; cycle detection; no `eval`/`exec` | **Implemented (v0.7)** |
| `salary_calculator.py` | Line specs → dependency order → fixed / % / formula → rounding | **Implemented (v0.7)** |
| `calculator.py` / `payroll_engine.calculate_run` | Run pipeline, proration, snapshots, partial errors | **Implemented (v0.8.2 / Sprint 8.2)** |
| `attendance_loader.py` / `salary_loader.py` | Period attendance + effective assignment | **Implemented (Sprint 8.2)** |
| `statutory.py` + `apps.compliance` | EPF + ESI + PT + TDS engines | **EPF Implemented (Sprint 9.1)**; **ESI Implemented (Sprint 9.2)**; **PT Implemented (Sprint 9.3)**; **TDS Implemented (Sprint 9.4)** |
| `payslip_generator.py` | Legacy payslip path | **Implemented (v0.7)** |
| `payslip_data.py` | Read-only payslip preview dataset from `PayrollResult` snapshots | **Implemented (Sprint 8.4)** |
| `report_queries.py` | Visibility-aware snapshot report queries, totals, and summaries | **Implemented (Sprint 8.4)** |
| `export_service.py` | Snapshot-only payroll-engine Excel exports | **Implemented (Sprint 8.4)** |
| `validation.py` | Structure / period / run calculable checks | **Implemented** |

### Net pay (run engine)

\[
\text{net} = \sum \text{prorated earnings} - \sum \text{prorated structure deductions} - \text{EE PF} - \text{VPF} - \text{EE ESI} - \text{PT} - \text{monthly TDS}
\]

### Related

- [Payroll lifecycle](lifecycle.md)
- [Data model](data-model.md)
- [Extension points](extension-points.md)
