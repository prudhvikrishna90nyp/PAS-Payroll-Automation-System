# DEPLOYMENT

## Prerequisites

- Python 3.12+
- Docker & Docker Compose (optional)
- PostgreSQL 14+ (production)

---

## Local Development

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements/dev.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/

---

## Git Workflow

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready releases |
| `develop` | Integration branch for all modules |
| `feature/<module-name>` | Per-module development (branch from `develop`) |

```bash
git checkout develop
git checkout -b feature/<module-name>
# commit work, push, open PR into develop
```

When a release is ready, merge `develop` → `main`.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes (prod) | — | Django secret key |
| `DEBUG` | No | `True` | Debug mode |
| `ALLOWED_HOSTS` | Yes (prod) | `localhost` | Comma-separated hosts |
| `DB_NAME` | No | — | PostgreSQL database name |
| `DB_USER` | No | `postgres` | Database user |
| `DB_PASSWORD` | No | — | Database password |
| `DB_HOST` | No | `localhost` | Database host |
| `DB_PORT` | No | `5432` | Database port |
| `CSRF_TRUSTED_ORIGINS` | Prod | — | HTTPS origins |
| `SECURE_SSL_REDIRECT` | Prod | `False` | Force HTTPS |

---

## Docker Deployment

```bash
cd backend
cp .env.example .env
# Edit .env with production values
docker compose up --build -d
```

Services:
- **web** — Gunicorn on port 8000
- **db** — PostgreSQL 17

Run migrations inside the container:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

---

## Manual Production Deployment

```bash
cd backend
pip install -r requirements/production.txt
export DJANGO_SETTINGS_MODULE=config.settings.production
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

---

## Production Checklist

- [ ] Set strong `SECRET_KEY`
- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set `CSRF_TRUSTED_ORIGINS` for your domain
- [ ] Use PostgreSQL (not SQLite)
- [ ] Enable HTTPS (`SECURE_SSL_REDIRECT=True`)
- [ ] Run `collectstatic` (WhiteNoise serves static files)
- [ ] Configure media storage (S3 or nginx for `/media/`)
- [ ] Set up database backups
- [ ] Create admin superuser

---

## Initial Data Setup

1. **Clients** → `/clients/add/`
2. **Companies** → `/company/companies/add/`
3. **Branches** → `/company/branches/add/`
4. **Admin → Departments** — Create departments
5. **Admin → Employees** — Add employees
6. **Admin → Pay periods** — Create a pay period
7. **Payroll → Payslips** — Generate payslips

---

## Settings Modules

| Module | Use |
|--------|-----|
| `config.settings.development` | Local dev (`manage.py`) |
| `config.settings.production` | Gunicorn / Docker |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| PDF generation fails on Windows | Install GTK3 runtime for WeasyPrint |
| Static files missing | Run `collectstatic` |
| CSRF error on login | Add domain to `CSRF_TRUSTED_ORIGINS` |
| Database connection refused | Check `DB_HOST` and PostgreSQL is running |
