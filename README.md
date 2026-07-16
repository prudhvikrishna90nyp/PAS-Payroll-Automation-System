# PAS — Payroll Automation System

Monorepo for the PAS payroll platform.

## Structure

```
PAS-Payroll-Automation-System/
│
├── docs/
│   ├── SRS.md
│   ├── ROADMAP.md
│   ├── DATABASE.md
│   ├── UI_GUIDE.md
│   ├── API.md
│   ├── DEPLOYMENT.md
│   └── CHANGELOG.md
├── backend/              # Django application
├── frontend/             # Phase 2 — React
└── README.md
```

## Quick Start

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

## Documentation

| Document | Description |
|----------|-------------|
| [SRS.md](docs/SRS.md) | Software requirements |
| [ROADMAP.md](docs/ROADMAP.md) | Development phases |
| [DATABASE.md](docs/DATABASE.md) | Schema reference |
| [UI_GUIDE.md](docs/UI_GUIDE.md) | Layout and design patterns |
| [API.md](docs/API.md) | Routes and endpoints |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Install and deploy |
| [CHANGELOG.md](docs/CHANGELOG.md) | Version history |

## Docker

```bash
cd backend
docker compose up --build
```

## Tests

```bash
cd backend
python manage.py test tests
```

## Frontend (Phase 2)

React SPA — see [frontend/README.md](frontend/README.md).
