# Locking rules

> Part of [PAS Architecture](../ARCHITECTURE.md). Status tags: **Implemented** vs **Planned**.

### Attendance period lock — **Implemented (v0.6)**

| Rule | Detail |
|------|--------|
| Editable when | `AttendancePeriod.status == open` |
| Blocked when | `locked` or `processed` — `assert_period_editable()` raises on create/edit/import |
| Allowed transitions | open↔locked, locked→processed, processed→locked |
| Reopen | locked→open only with `reopen_attendanceperiod` |
| Summary | Regenerated on lock |

### Payroll immutability — **Planned (Sprint 8 / v0.8+)** goals

| Goal | Today | Target |
|------|-------|--------|
| Finalized payslip | Not overwritten by `generate_payslip` | Keep; add UI finalize + audit |
| Closed pay period | `is_closed` unused in generator | Block regenerate / edits when closed |
| Attendance → payroll | Summaries not yet applied to pay | After period `processed`, freeze LOP/OT inputs into run |
| Correction path | Re-generate draft | Controlled reopen + correction payslip / arrears |

### Related

- [Approval workflow](approval-workflow.md)
- [Payroll lifecycle](lifecycle.md)
|
