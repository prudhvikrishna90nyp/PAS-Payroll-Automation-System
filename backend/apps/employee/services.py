from apps.employee.models import Employee


def generate_employee_code(company):
    prefix = 'EMP'
    existing_codes = Employee.all_objects.filter(
        company=company,
        employee_code__startswith=prefix,
    ).values_list('employee_code', flat=True)

    max_number = 0
    for code in existing_codes:
        suffix = code[len(prefix):]
        if suffix.isdigit():
            max_number = max(max_number, int(suffix))

    return f'{prefix}{max_number + 1:04d}'
