# PAS Knowledge Base

Numbered documentation for PAS — Payroll Automation System. Read in order for full project context, or jump to the topic you need.

```
backend/docs/
│
├── 01_SRS.md
├── 02_DATABASE.md
├── 03_UI_GUIDE.md
├── 04_API.md
├── 05_DEPLOYMENT.md
├── 06_CHANGELOG.md
├── 07_ROADMAP.md
└── 08_ARCHITECTURE.md          # pointer → docs/ARCHITECTURE.md + payroll-architecture/
```

Root architecture (canonical content):

```
docs/
├── ARCHITECTURE.md
└── payroll-architecture/
    ├── lifecycle.md
    ├── calculation-sequence.md
    ├── approval-workflow.md
    ├── locking-rules.md
    ├── data-model.md
    └── extension-points.md
```

| # | Document | Description |
|---|----------|-------------|
| 01 | [SRS](01_SRS.md) | Software requirements, tech stack, coding standards |
| 02 | [Database](02_DATABASE.md) | Schema and data model reference |
| 03 | [UI Guide](03_UI_GUIDE.md) | Layout, components, and design patterns |
| 04 | [API](04_API.md) | Routes, endpoints, and URL map |
| 05 | [Deployment](05_DEPLOYMENT.md) | Local setup, Docker, and production |
| 06 | [Changelog](06_CHANGELOG.md) | Version history |
| 07 | [Roadmap](07_ROADMAP.md) | Development phases and planned work |
| 08 | [Architecture](08_ARCHITECTURE.md) | Pointer to root overview and [`docs/payroll-architecture/`](../../docs/payroll-architecture/) |
| — | [Root architecture](../../docs/ARCHITECTURE.md) | Payroll overview, code map, version alignment, topic index |
