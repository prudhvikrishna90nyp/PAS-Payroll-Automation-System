# PAS — Payroll Automation System

Monorepo for the PAS payroll platform.

**Current release:** [v1.0.0](docs/RELEASE_NOTES_v1.0.0.md) (first production GA)

## Structure

```
PAS-Payroll-Automation-System/
│
├── backend/
│   ├── apps/
│   │   ├── accounts/
│   │   ├── dashboard/
│   │   ├── clients/
│   │   ├── company/
│   │   ├── employee/
│   │   ├── attendance/
│   │   ├── leave/
│   │   ├── payroll/
│   │   ├── reports/
│   │   ├── compliance/
│   │   ├── notifications/
│   │   ├── audit/
│   │   └── common/
│   ├── config/
│   ├── templates/
│   ├── static/
│   ├── media/
│   ├── docs/             # Project knowledge base
│   │   ├── 01_SRS.md
│   │   ├── 02_DATABASE.md
│   │   ├── 03_UI_GUIDE.md
│   │   ├── 04_API.md
│   │   ├── 05_DEPLOYMENT.md
│   │   ├── 06_CHANGELOG.md
│   │   └── 07_ROADMAP.md
│   ├── requirements/
│   ├── tests/
│   ├── manage.py
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── frontend/             # Phase 2 — React
├── .gitignore
├── LICENSE
└── README.md
```

## Git Workflow

Three-branch strategy:

```
main                      ← production-ready releases
develop                   ← integration branch
feature/<module-name>     ← module work (e.g. feature/client-management)
```

| Branch | Purpose |
|--------|---------|
| `main` | Stable, deployable code. Merges from `develop` at release time. |
| `develop` | Ongoing integration. All feature branches merge here. |
| `feature/<module-name>` | Single module or feature. Branch from `develop`, merge back via PR. |

**Typical flow:**

```bash
git checkout develop
git pull origin develop
git checkout -b feature/client-management

# ... work, commit ...

git push -u origin feature/client-management
# Open PR: feature/client-management → develop

# After release:
# PR: develop → main
```

**Naming examples:** `feature/client-management`, `feature/company-management`, `feature/payroll`

---

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

Project knowledge base: [backend/docs/](backend/docs/)

| Document | Description |
|----------|-------------|
| [01_SRS.md](backend/docs/01_SRS.md) | Software requirements |
| [02_DATABASE.md](backend/docs/02_DATABASE.md) | Schema reference |
| [03_UI_GUIDE.md](backend/docs/03_UI_GUIDE.md) | Layout and design patterns |
| [04_API.md](backend/docs/04_API.md) | Routes and endpoints |
| [05_DEPLOYMENT.md](backend/docs/05_DEPLOYMENT.md) | Install and deploy |
| [06_CHANGELOG.md](backend/docs/06_CHANGELOG.md) | Version history |
| [07_ROADMAP.md](backend/docs/07_ROADMAP.md) | Development phases |

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

## License

MIT — see [LICENSE](LICENSE).
