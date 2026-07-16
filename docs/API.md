# PayrollAutomation — Routes & Endpoints

The application currently serves HTML views (not a REST API). All routes below are web endpoints unless noted.

Base URL (development): `http://127.0.0.1:8000`

---

## Dashboard

| Method | URL | Name | Auth | Description |
|--------|-----|------|------|-------------|
| GET | `/` | dashboard | Required | Home dashboard |

---

## Accounts

| Method | URL | Name | Auth | Description |
|--------|-----|------|------|-------------|
| GET | `/accounts/profile/` | profile | Required | User profile page |

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
| GET | `/payroll/payslips/` | payslip_list | Open | List payslips (filter by `?period=<id>`) |
| GET | `/payroll/payslips/<id>/` | payslip_detail | Open | Payslip detail |
| GET | `/payroll/payslips/<id>/pdf/` | payslip_pdf | Open | Download payslip PDF |
| GET | `/payroll/payslips/export/` | payslip_export_excel | Open | Export Excel (`?period=<id>` optional) |
| POST | `/payroll/pay-periods/<id>/generate/` | generate_period_payslips | Open | Generate payslips for period |

---

## Reports

| Method | URL | Name | Auth | Description |
|--------|-----|------|------|-------------|
| GET | `/reports/` | reports_index | Open | Reports summary and links |

---

## Admin

| Method | URL | Description |
|--------|-----|-------------|
| GET/POST | `/admin/` | Django admin (Company, Employee, Payroll, Attendance) |
| GET | `/admin/login/` | Login |
| POST | `/admin/logout/` | Logout |

---

## Static & Media

| Path | Description |
|------|-------------|
| `/static/` | CSS, JS, images (WhiteNoise in production) |
| `/media/` | Uploaded files (company logos) — development only via Django |

---

## Future REST API (Planned)

A JSON REST API under `/api/v1/` is planned for Phase 4. Endpoints will cover employees, payroll runs, payslips, and statutory reports.
