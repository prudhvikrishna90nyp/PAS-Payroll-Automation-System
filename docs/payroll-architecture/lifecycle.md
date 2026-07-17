# Payroll lifecycle

> Part of [PAS Architecture](../ARCHITECTURE.md). Status tags: **Implemented** vs **Planned**.

End-to-end flow from attendance close through bank advice. Solid boxes are implemented; dashed boxes are planned.

```mermaid
flowchart LR
  subgraph attendance ["Attendance (v0.6)"]
    A1[Daily Attendance] --> A2[Approve days]
    A2 --> A3[Lock AttendancePeriod]
    A3 --> A4[AttendanceMonthlySummary]
  end

  subgraph salary ["Salary masters (v0.7)"]
    S1[SalaryComponent] --> S2[SalaryStructure + Lines]
    S2 --> S3[EmployeeSalaryAssignment]
  end

  subgraph calc ["Calculation (v0.7)"]
    C1[Formula engine] --> C2[salary_calculator]
    C2 --> C3[Statutory stubs]
    C3 --> C4[Net pay]
  end

  subgraph engine ["Payroll engine (v0.8.1–8.2)"]
    P1[PayrollPeriod Open/Closed] --> P2[PayrollRun Draft…]
    P2 --> P3[calculate_run + proration]
    P3 --> P5[PayrollResult + Components]
    P2 --> P4[PayrollAuditLog]
  end

  subgraph output ["Output"]
    O1[Payslip preview + reports] --> O2[PDF planned / Excel]
    O3["Bank advice (planned)"]
  end

  A4 --> C2
  S3 --> C2
  C4 --> O1
  O1 -.-> O3
  A3 -.->|period processed| P1
  A4 --> P3
  S3 --> P3
  P5 -.->|wire later| O1
```

### Step summary

| Step | Behaviour | Status |
|------|-----------|--------|
| 1. Attendance capture | Daily `Attendance` (P/A/H/WO/CL/SL/EL/LOP/HD/OD), shifts, holidays, import/export | **Implemented (v0.6)** |
| 2. Attendance approval | Per-row `approved` flag on daily attendance | **Implemented (v0.6)** — no multi-step workflow UI |
| 3. Period lock | `AttendancePeriod`: open → locked → processed; lock rebuilds monthly summaries | **Implemented (v0.6)** |
| 4. Salary assignment | Component masters → structure lines → `EmployeeSalaryAssignment` (effective dating) | **Implemented (v0.7)** |
| 5. Formula calculation | Safe AST formula engine + dependency order + rounding | **Implemented (v0.7)** |
| 6. Statutory | `compliance.pf_engine` + `statutory.py` bridges | **EPF Implemented (Sprint 9.1)**; ESI/PT/TDS **Planned (9.2–9.4)** |
| 7. Net → payslip | `generate_payslip` writes `Payslip` + `PayslipItem`; skips if `finalized` | **Implemented (v0.7)** |
| 8. Bank advice | Employee bank fields exist; dedicated NEFT/advice export | **Planned (v0.8+)** |
| 9. Payroll period / run foundation | `PayrollPeriod` (Open/Closed, overlap checks), `PayrollRun` (Draft+status scaffold), `PayrollResult` / `PayrollResultComponent`, `PayrollAuditLog`; services under `apps/payroll/services/` | **Implemented (v0.8.1 foundation)** |
| 10. Run calculation | `calculate_run`: attendance + effective assignment + formula + proration → results; Incomplete on per-employee errors; recalculate unlocked | **Implemented (Sprint 8.2)** |
| 11. Approval / lock | Reviewed → Approved → Locked immutability | **Implemented (Sprint 8.3)** |
| 12. Reports / payslip preparation | Snapshot-only on-screen payroll reports, Excel exports, and draft/final payslip preview; PDF rendering remains deferred | **Implemented (Sprint 8.4)** |

**Legacy:** `PayPeriod` / `Payslip` remain for existing payslip generation. `PayrollPeriod` / `PayrollRun` snapshots now supply report and preview data; PDF generation remains planned.

**Proration (Sprint 8.2):** calendar days in period vs payable days (eligible days after mid-month join / exit; LOP; half-day = 0.5 present). See [calculation-sequence.md](calculation-sequence.md).

### Related

- [Calculation sequence](calculation-sequence.md)
- [Approval workflow](approval-workflow.md)
- [Locking rules](locking-rules.md)
|
