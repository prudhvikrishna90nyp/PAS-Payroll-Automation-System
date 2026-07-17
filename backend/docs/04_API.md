# API

Base URL (development): `http://127.0.0.1:8000`

Currently HTML views only. REST API planned for Phase 2 under `/api/v1/`.

---

## Dashboard

| Method | URL | Name | Auth | Description |
|--------|-----|------|------|-------------|
| GET | `/` | dashboard | Required | Home dashboard |

---

## Accounts

| Method | URL | Name | Auth | Description |
|--------|-----|------|------|-------------|
| GET | `/accounts/profile/` | profile | Required | User profile |

---

## Client Management

| Method | URL | Name | Auth | Description |
|--------|-----|------|------|-------------|
| GET | `/clients/` | clients:client_list | Required | List clients (`?q=`, `?status=`, `?page=`) |
| GET/POST | `/clients/add/` | clients:client_add | Required | Create client |
| GET | `/clients/<id>/` | clients:client_detail | Required | Client detail |
| GET/POST | `/clients/<id>/edit/` | clients:client_edit | Required | Edit client |
| POST | `/clients/<id>/archive/` | clients:client_archive | Required | Archive (soft delete) |
| POST | `/clients/<id>/restore/` | clients:client_restore | Required | Restore archived client |

---

## Company Management

| Method | URL | Name | Auth | Description |
|--------|-----|------|------|-------------|
| GET | `/companies/` | company:company_list | Required | List companies (`?q=`, `?client=`, `?status=`) |
| GET | `/companies/<id>/` | company:company_detail | Required | Company detail |
| GET/POST | `/companies/add/` | company:company_add | Required | Create company (multipart for logo) |
| GET/POST | `/companies/<id>/edit/` | company:company_edit | Required | Edit company |
| POST | `/companies/<id>/archive/` | company:company_archive | Required | Archive company |
| POST | `/companies/<id>/restore/` | company:company_restore | Required | Restore company |
| GET | `/branches/` | organisation:branch_list | Required | List branches (`?q=`, `?client=`, `?company=`, `?status=`) |
| GET | `/branches/<id>/` | organisation:branch_detail | Required | Branch detail |
| GET/POST | `/branches/add/` | organisation:branch_add | Required | Create branch |
| GET/POST | `/branches/<id>/edit/` | organisation:branch_edit | Required | Edit branch |
| POST | `/branches/<id>/archive/` | organisation:branch_archive | Required | Archive branch |
| POST | `/branches/<id>/restore/` | organisation:branch_restore | Required | Restore branch |
| GET | `/departments/` | organisation:department_list | Required | List departments (`?q=`, `?company=`, `?status=`) |
| GET | `/departments/<id>/` | organisation:department_detail | Required | Department detail |
| GET/POST | `/departments/add/` | organisation:department_add | Required | Create department |
| GET/POST | `/departments/<id>/edit/` | organisation:department_edit | Required | Edit department |
| POST | `/departments/<id>/archive/` | organisation:department_archive | Required | Archive department |
| POST | `/departments/<id>/restore/` | organisation:department_restore | Required | Restore department |
| GET | `/designations/` | organisation:designation_list | Required | List designations (`?q=`, `?company=`, `?status=`) |
| GET | `/designations/<id>/` | organisation:designation_detail | Required | Designation detail |
| GET/POST | `/designations/add/` | organisation:designation_add | Required | Create designation |
| GET/POST | `/designations/<id>/edit/` | organisation:designation_edit | Required | Edit designation |
| POST | `/designations/<id>/archive/` | organisation:designation_archive | Required | Archive designation |
| POST | `/designations/<id>/restore/` | organisation:designation_restore | Required | Restore designation |

### Employees (`/employees/`)

| Method | URL | Name | Auth | Description |
|--------|-----|------|------|-------------|
| GET | `/employees/` | employees:employee_list | Required | List employees with advanced filters |
| GET | `/employees/<id>/` | employees:employee_detail | Required | Employee profile with documents |
| GET/POST | `/employees/add/` | employees:employee_add | Required | Create employee (multipart for photo) |
| GET/POST | `/employees/<id>/edit/` | employees:employee_edit | Required | Edit employee |
| POST | `/employees/<id>/archive/` | employees:employee_archive | Required | Archive employee |
| POST | `/employees/<id>/restore/` | employees:employee_restore | Required | Restore employee |
| GET/POST | `/employees/import/` | employees:employee_import | Required | Bulk Excel import |
| GET | `/employees/export/` | employees:employee_export | Required | Excel export (`?company=`, `?template=1`) |

---

## Employee

| Method | URL | Name | Auth | Description |
|--------|-----|------|------|-------------|
| GET | `/employee/` | employee_list | Open | List active employees |

---

## Attendance

| Method | URL | Name | Auth | Description |
|--------|-----|------|------|-------------|
| GET | `/attendance/` | attendance_list | Open | Recent attendance records |

---

## Payroll

| Method | URL | Name | Auth | Description |
|--------|-----|------|------|-------------|
| GET | `/payroll/payslips/` | payslip_list | Open | List payslips (`?period=<id>`) |
| GET | `/payroll/payslips/<id>/` | payslip_detail | Open | Payslip detail |
| GET | `/payroll/payslips/<id>/pdf/` | payslip_pdf | Open | Download PDF |
| GET | `/payroll/payslips/export/` | payslip_export_excel | Open | Export Excel |
| POST | `/payroll/pay-periods/<id>/generate/` | generate_period_payslips | Open | Generate payslips |

---

## Reports

| Method | URL | Name | Auth | Description |
|--------|-----|------|------|-------------|
| GET | `/reports/` | reports_index | Open | Reports summary |

---

## Admin

| Method | URL | Description |
|--------|-----|-------------|
| GET/POST | `/admin/` | Django admin |
| GET | `/admin/login/` | Login |
| POST | `/admin/logout/` | Logout |

---

## Static & Media

| Path | Description |
|------|-------------|
| `/static/` | CSS, JS (WhiteNoise in production) |
| `/media/` | Uploaded logos (dev only via Django) |

---

## Future REST API (Phase 2)

```
GET    /api/v1/clients/
POST   /api/v1/clients/
GET    /api/v1/companies/
POST   /api/v1/payroll/generate/
GET    /api/v1/payslips/{id}/
GET    /api/v1/employees/
```

Authentication: JWT or session-based (TBD).
