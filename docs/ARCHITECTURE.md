# PAS Architecture — Payroll Reference

Production-oriented reference for how PAS runs payroll today (v0.6–v0.7) and what is planned for v0.8+.

Detailed topics live under [`payroll-architecture/`](payroll-architecture/). The numbered knowledge base entry is a short pointer: [`backend/docs/08_ARCHITECTURE.md`](../backend/docs/08_ARCHITECTURE.md).

| Related docs | Path |
|--------------|------|
| SRS / stack | [01_SRS.md](../backend/docs/01_SRS.md) |
| Schema detail | [02_DATABASE.md](../backend/docs/02_DATABASE.md) |
| HTML URL map | [04_API.md](../backend/docs/04_API.md) |
| Version history | [06_CHANGELOG.md](../backend/docs/06_CHANGELOG.md) |
| Phased roadmap | [07_ROADMAP.md](../backend/docs/07_ROADMAP.md) |
| Numbered architecture pointer | [08_ARCHITECTURE.md](../backend/docs/08_ARCHITECTURE.md) |

**Status legend**

| Tag | Meaning |
|-----|---------|
| **Implemented (v0.6–v0.7)** | Present in code on `main` (attendance Sprint 6, salary structures Sprint 7) |
| **Planned (v0.8+)** | Designed or stubbed; not yet production-complete |

---

## Topic index

| Topic | Document |
|-------|----------|
| Payroll lifecycle | [payroll-architecture/lifecycle.md](payroll-architecture/lifecycle.md) |
| Calculation sequence | [payroll-architecture/calculation-sequence.md](payroll-architecture/calculation-sequence.md) |
| Approval workflow | [payroll-architecture/approval-workflow.md](payroll-architecture/approval-workflow.md) |
| Locking rules | [payroll-architecture/locking-rules.md](payroll-architecture/locking-rules.md) |
| Data model | [payroll-architecture/data-model.md](payroll-architecture/data-model.md) |
| Extension points | [payroll-architecture/extension-points.md](payroll-architecture/extension-points.md) |

---

## Overview

End-to-end payroll runs from attendance close through bank advice:

1. Capture and approve daily attendance, then lock the attendance period (**Implemented (v0.6)**).
2. Assign salary structures with formula-driven components (**Implemented (v0.7)**).
3. Generate draft payslips via the calculation engines; finalized slips are not overwritten (**Implemented (v0.7)**).
4. Bank advice export, attendance-linked proration, and pay-period immutability are **Planned (v0.8+)**.

See [lifecycle.md](payroll-architecture/lifecycle.md) for the full flowchart and step table.

---

## Code map (quick reference)

| Area | Location |
|------|----------|
| Attendance models / lock | `apps/attendance/models.py`, `apps/attendance/services.py` |
| Payroll models | `apps/payroll/models.py` |
| Formula / salary / payslip / statutory | `apps/payroll/services/*.py` |
| Payroll HTML routes | `apps/payroll/urls.py` → [04_API.md](../backend/docs/04_API.md) |
| Attendance HTML routes | `apps/attendance/urls.py` |
| Org hierarchy | `apps/clients`, `apps/company`, `apps/employee` |

---

## Version alignment

| Version | Theme |
|---------|-------|
| **v0.6** | Attendance management, period lock, monthly summary |
| **v0.7** | Component salary structures, formula engine, assignment-aware payslips, statutory stubs |
| **v0.8+** | Attendance-linked payroll, payroll period immutability, bank advice, full statutory engines, payslip approval UX |
|
