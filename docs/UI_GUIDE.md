# UI GUIDE

## Design System

PAS uses **Bootstrap 5.3** with **Bootstrap Icons** and a custom sidebar layout defined in `backend/static/css/dashboard.css`.

---

## Layout Structure

```
┌─────────────┬──────────────────────────────────┐
│   Sidebar   │  Top Navbar (user menu, toggle)  │
│   (left)    ├──────────────────────────────────┤
│             │  Page heading + subtitle         │
│             │  Content area                    │
│             ├──────────────────────────────────┤
│             │  Footer                          │
└─────────────┴──────────────────────────────────┘
```

### Template files

| File | Purpose |
|------|---------|
| `backend/templates/base.html` | Master layout |
| `backend/templates/includes/sidebar.html` | Left navigation |
| `backend/templates/includes/navbar.html` | Top bar + user dropdown |
| `backend/templates/includes/footer.html` | Footer |

---

## Branding

| Variable | Value |
|----------|-------|
| Short name | PAS |
| Full name | Payroll Automation System |
| Primary color | `#2563eb` (blue) |
| Sidebar background | `#0f172a` (dark slate) |

Branding is injected via `payroll_project.context_processors.branding`.

---

## Navigation (Sidebar)

| Icon | Label | URL |
|------|-------|-----|
| speedometer | Dashboard | `/` |
| briefcase | Clients | `/company/clients/` |
| building | Companies | `/company/companies/` |
| diagram-3 | Branches | `/company/branches/` |
| people | Employees | `/employee/` |
| calendar-check | Attendance | `/attendance/` |
| cash-stack | Payroll | `/payroll/payslips/` |
| bar-chart | Reports | `/reports/` |
| gear | Admin | `/admin/` |

Active link highlighting uses `request.resolver_match.url_name`.

---

## Page Patterns

### List pages

- Search input + status filter + entity filters
- Bootstrap table (`table-hover`, `table-light` header)
- Pagination (10 items per page)
- Add button (top right)
- Edit / Delete actions per row

### Form pages

- Card wrapper (`border-0 shadow-sm`)
- Bootstrap form controls (`form-control`, `form-select`)
- Field-level error messages in red
- Save / Cancel buttons

### Dashboard

- Quick-access stat cards in a responsive grid
- Welcome message card

---

## Creating a New Page

```django
{% extends 'base.html' %}

{% block title %}My Page - PAS{% endblock %}
{% block page_heading %}My Page{% endblock %}
{% block page_subtitle %}Description here{% endblock %}

{% block content %}
<div class="card border-0 shadow-sm">
    <div class="card-body">
        <!-- content -->
    </div>
</div>
{% endblock %}
```

---

## Responsive Behavior

- **Desktop:** Fixed sidebar (260px) + content area
- **Mobile (<992px):** Sidebar hidden off-canvas, toggled via hamburger button in navbar

---

## Phase 2 (React)

The `frontend/` folder will host a React SPA that replaces Django templates for interactive screens. The backend will expose a REST API. Shared design tokens (colors, spacing) should match this guide.
