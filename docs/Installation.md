# PayrollAutomation — Installation

## Project Structure

```
PayrollAutomation/
│
├── docs/
│   ├── Roadmap.md
│   ├── Database.md
│   ├── API.md
│   └── Installation.md
│
├── payroll_project/       # Django settings, URLs, WSGI
├── dashboard/
├── company/
├── employee/
├── attendance/
├── payroll/
├── reports/
├── templates/
├── static/
├── media/
├── manage.py
└── requirements.txt
```

> **Note:** `accounts/` handles user profile routes. `payroll_project/` is the Django configuration package (required but not shown in all diagrams).

---

## Requirements

- Python 3.12+
- pip
- (Optional) PostgreSQL 14+ for production
- (Optional) GTK3 runtime for WeasyPrint PDF on Windows

---

## Setup

### 1. Clone and enter the project

```bash
cd PayrollAutomation
```

### 2. Create virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # Linux / macOS
```

Edit `.env`:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

For PostgreSQL, uncomment and set:

```env
DB_NAME=payroll
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432
```

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Create admin user

```bash
python manage.py createsuperuser
```

### 7. Run development server

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/

---

## Production Deployment

### Collect static files

```bash
python manage.py collectstatic
```

### Run with Gunicorn

```bash
set DJANGO_SETTINGS_MODULE=payroll_project.settings.production   # Windows
export DJANGO_SETTINGS_MODULE=payroll_project.settings.production  # Linux

gunicorn payroll_project.wsgi:application --bind 0.0.0.0:8000
```

### Production checklist

- Set a strong `SECRET_KEY` in `.env`
- Set `DEBUG=False`
- Configure `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`
- Use PostgreSQL
- Enable HTTPS (`SECURE_SSL_REDIRECT=True`)
- Serve media files via object storage or reverse proxy

---

## Initial Data Setup

1. **Admin → Companies** — Add company master details
2. **Admin → Departments** — Create departments
3. **Admin → Employees** — Add employees with salary
4. **Admin → Pay periods** — Create a pay period
5. **Payroll → Payslips** — Generate payslips for the period
