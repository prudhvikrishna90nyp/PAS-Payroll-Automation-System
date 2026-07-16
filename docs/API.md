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

## Company Management

| Method | URL | Name | Auth | Description |
|--------|-----|------|------|-------------|
| GET | `/company/clients/` | client_list | Required | List clients (`?q=`, `?status=`, `?page=`) |
| GET/POST | `/company/clients/add/` | client_create | Required | Create client |
| GET/POST | `/company/clients/<id>/edit/` | client_update | Required | Edit client |
| POST | `/company/clients/<id>/delete/` | client_delete | Required | Soft delete |
| GET | `/company/companies/` | company_list | Required | List companies (`?q=`, `?client=`, `?status=`) |
| GET/POST | `/company/companies/add/` | company_create | Required | Create company (multipart for logo) |
| GET/POST | `/company/companies/<id>/edit/` | company_update | Required | Edit company |
| POST | `/company/companies/<id>/delete/` | company_delete | Required | Soft delete |
| GET | `/company/branches/` | branch_list | Required | List branches (`?q=`, `?client=`, `?company=`) |
| GET/POST | `/company/branches/add/` | branch_create | Required | Create branch |
| GET/POST | `/company/branches/<id>/edit/` | branch_update | Required | Edit branch |
| POST | `/company/branches/<id>/delete/` | branch_delete | Required | Soft delete |

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
