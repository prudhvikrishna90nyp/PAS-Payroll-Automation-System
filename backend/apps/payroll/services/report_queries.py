"""Read-only reporting queries over immutable payroll result snapshots."""
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce

from apps.employee.models import Employee
from apps.payroll.models import ComponentType, PayrollResult, PayrollResultComponent, PayrollRun, PayrollRunStatus

FINAL_RUN_STATUSES = ("approved", "locked")
DRAFTISH = ("draft", "calculated", "incomplete", "reviewed")
VISIBILITY_FINAL = "final"
VISIBILITY_DRAFT = "draft"
VISIBILITY_ALL = "all"
ZERO = Decimal("0.00")


def _value(params, *names):
    for name in names:
        value = params.get(name) if hasattr(params, "get") else None
        if value not in (None, ""):
            return value
    return None


def _ids(value):
    if value in (None, ""):
        return []
    if isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = str(value).split(",")
    output = []
    for item in values:
        try:
            output.append(int(item))
        except (TypeError, ValueError):
            pass
    return output


@dataclass(frozen=True)
class ReportFilters:
    company_ids: tuple = ()
    period_ids: tuple = ()
    run_ids: tuple = ()
    branch_ids: tuple = ()
    department_ids: tuple = ()
    employee_search: str = ""
    visibility: str = VISIBILITY_FINAL
    user: object = None

    @classmethod
    def from_params(cls, params, user=None):
        visibility = str(_value(params, "visibility") or VISIBILITY_FINAL).lower()
        if visibility not in (VISIBILITY_FINAL, VISIBILITY_DRAFT, VISIBILITY_ALL):
            visibility = VISIBILITY_FINAL
        return cls(
            company_ids=tuple(_ids(_value(params, "company", "company_id", "company_ids"))),
            period_ids=tuple(_ids(_value(params, "period", "period_id", "period_ids"))),
            run_ids=tuple(_ids(_value(params, "run", "run_id", "run_ids"))),
            branch_ids=tuple(_ids(_value(params, "branch", "branch_id", "branch_ids"))),
            department_ids=tuple(_ids(_value(params, "department", "department_id", "department_ids"))),
            employee_search=str(_value(params, "employee", "employee_search", "search", "q") or "").strip(),
            visibility=visibility,
            user=user,
        )


def companies_visible_to_user(user):
    """Return None for unrestricted users, otherwise visible company ids."""
    if user is None:
        return None
    if getattr(user, "is_superuser", False) or any(
        user.has_perm(permission)
        for permission in ("payroll.view_payrollresult", "payroll.view_payrollrun")
    ):
        return None
    # This project has no company-scoped role relation; no global permission means no rows.
    return []


def is_final_status(status):
    return status in FINAL_RUN_STATUSES


def status_label_for_display(status):
    try:
        return PayrollRunStatus(status).label
    except ValueError:
        return str(status or "").replace("_", " ").title()


def _employee_ids(filters):
    employees = Employee.all_objects.all()
    if filters.branch_ids:
        employees = employees.filter(branch_id__in=filters.branch_ids)
    if filters.department_ids:
        employees = employees.filter(department_id__in=filters.department_ids)
    if filters.employee_search:
        term = filters.employee_search
        employees = employees.filter(
            Q(employee_code__icontains=term) | Q(first_name__icontains=term) |
            Q(last_name__icontains=term) | Q(email__icontains=term)
        )
    return employees.values("pk")


def results_queryset(filters):
    qs = PayrollResult.objects.select_related("run", "run__company", "run__period")
    visible = companies_visible_to_user(filters.user)
    if visible is not None:
        qs = qs.filter(run__company_id__in=visible)
    if filters.company_ids:
        qs = qs.filter(run__company_id__in=filters.company_ids)
    if filters.period_ids:
        qs = qs.filter(run__period_id__in=filters.period_ids)
    if filters.run_ids:
        qs = qs.filter(run_id__in=filters.run_ids)
    if filters.branch_ids or filters.department_ids or filters.employee_search:
        qs = qs.filter(employee_id__in=_employee_ids(filters))
    if filters.visibility == VISIBILITY_FINAL:
        qs = qs.filter(run__status__in=FINAL_RUN_STATUSES)
    elif filters.visibility == VISIBILITY_DRAFT:
        qs = qs.filter(run__status__in=DRAFTISH)
    return qs.order_by("run__company__company_name", "run__period__year", "run__period__month", "run__run_number", "employee_id")


def load_employees_map(ids):
    return Employee.all_objects.select_related("branch", "department", "designation").in_bulk(ids)


def aggregate_result_totals(qs):
    return qs.aggregate(
        employee_count=Count("id"),
        gross=Coalesce(Sum("gross"), ZERO),
        total_earnings=Coalesce(Sum("total_earnings"), ZERO),
        total_deductions=Coalesce(Sum("total_deductions"), ZERO),
        net_salary=Coalesce(Sum("net_salary"), ZERO),
        ctc_snapshot=Coalesce(Sum("ctc_snapshot"), ZERO),
    )


def component_queryset(filters, component_type=None):
    qs = PayrollResultComponent.objects.filter(result__in=results_queryset(filters)).select_related(
        "result", "result__run", "result__run__company", "result__run__period"
    )
    if component_type:
        qs = qs.filter(component_type=component_type)
    return qs.order_by("component_code", "result__employee_id")


def aggregate_component_totals(qs):
    return qs.aggregate(amount=Coalesce(Sum("amount"), ZERO))


def reconcile_earnings_deductions(filters):
    results = aggregate_result_totals(results_queryset(filters))
    earnings = aggregate_component_totals(component_queryset(filters, ComponentType.EARNING))["amount"]
    deductions = aggregate_component_totals(component_queryset(filters, ComponentType.DEDUCTION))["amount"]
    return {
        "result_earnings": results["total_earnings"], "component_earnings": earnings,
        "result_deductions": results["total_deductions"], "component_deductions": deductions,
        "earnings_difference": results["total_earnings"] - earnings,
        "deductions_difference": results["total_deductions"] - deductions,
    }


@dataclass(frozen=True)
class SummaryRow:
    id: int | None
    name: str
    employee_count: int
    gross: Decimal
    total_earnings: Decimal
    total_deductions: Decimal
    net_salary: Decimal


def _summary(filters, field, name_field):
    rows = []
    for row in results_queryset(filters).values(field, name_field).annotate(
        employee_count=Count("pk"), gross=Coalesce(Sum("gross"), ZERO),
        total_earnings=Coalesce(Sum("total_earnings"), ZERO),
        total_deductions=Coalesce(Sum("total_deductions"), ZERO), net_salary=Coalesce(Sum("net_salary"), ZERO),
    ).order_by(name_field):
        rows.append(SummaryRow(row[field], row[name_field] or "Unassigned", row["employee_count"], row["gross"], row["total_earnings"], row["total_deductions"], row["net_salary"]))
    result_totals = aggregate_result_totals(results_queryset(filters))
    totals = {
        "employee_count": sum(row.employee_count for row in rows),
        **result_totals,
    }
    return rows, totals


def _employee_master_summary(filters, attribute, label_attribute):
    """Group snapshots by employee master data, including archived employees."""
    results = list(results_queryset(filters))
    employees = load_employees_map(result.employee_id for result in results)
    buckets = {}
    for result in results:
        employee = employees.get(result.employee_id)
        master = getattr(employee, attribute, None) if employee else None
        key = master.pk if master else None
        bucket = buckets.setdefault(key, {
            "name": getattr(master, label_attribute, None) or "Unassigned",
            "employee_count": 0,
            "gross": ZERO,
            "total_earnings": ZERO,
            "total_deductions": ZERO,
            "net_salary": ZERO,
        })
        bucket["employee_count"] += 1
        bucket["gross"] += result.gross or ZERO
        bucket["total_earnings"] += result.total_earnings or ZERO
        bucket["total_deductions"] += result.total_deductions or ZERO
        bucket["net_salary"] += result.net_salary or ZERO
    rows = [
        SummaryRow(
            key, bucket["name"], bucket["employee_count"], bucket["gross"],
            bucket["total_earnings"], bucket["total_deductions"], bucket["net_salary"],
        )
        for key, bucket in buckets.items()
    ]
    rows.sort(key=lambda row: (row.name.lower(), row.id is None, row.id or 0))
    return rows, aggregate_result_totals(results_queryset(filters))


def department_summary(filters):
    return _employee_master_summary(filters, "department", "name")


def branch_summary(filters):
    return _employee_master_summary(filters, "branch", "branch_name")


def company_summary(filters):
    return _summary(filters, "run__company_id", "run__company__company_name")


def run_control_queryset(filters):
    return PayrollRun.objects.filter(results__in=results_queryset(filters)).select_related("company", "period").distinct().order_by("company__company_name", "period__year", "period__month", "run_number")


def prefetch_components(qs):
    return qs.prefetch_related("components")

