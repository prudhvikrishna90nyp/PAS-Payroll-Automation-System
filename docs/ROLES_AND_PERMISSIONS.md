# Roles and Permissions (v1.0.0-rc1)

PAS uses Django Groups seeded on `post_migrate`. Assign users to exactly one primary group (or combine carefully).

## Groups

| Group | Typical use |
|-------|-------------|
| Super Admin | Full masters + payroll approve/lock + reopen (superuser flag still required for reopen) |
| Admin | Full operational control including approve/lock and compliance exports |
| HR | Employees, attendance, review payroll, limited compliance exports |
| Payroll | Runs, calculate, review, salary masters, compliance exports |
| Viewer | Read-only masters / runs / payslips |

## Critical rules (RC1)

- Legacy payslip URLs require `payroll.view_payslip` (generate requires `add_payslip`).
- Client / company / branch / department / designation mutate and archive require model permissions.
- Compliance Excel/ECR/Form 16 exports require `compliance.export_*` permissions (seeded for Admin/Payroll/HR as applicable).
- Payroll reopen is **superuser-only** with mandatory remarks; status returns to **Calculated** for recalculation.
- Employee seed **merges** permissions and must not be replaced by a wipe-style `set()` of only employee perms.

## Verification after migrate

```bash
python manage.py shell -c "from django.contrib.auth.models import Group; g=Group.objects.get(name='Admin'); print(sorted(g.permissions.values_list('codename', flat=True))[:20])"
```

Confirm Admin includes `view_payrollrun`, `approve_payrollrun`, `export_pfregister`, `add_company`, `view_employee`.
