from io import BytesIO

from django.http import HttpResponse
from openpyxl import Workbook, load_workbook

from .models import Employee

EXPORT_HEADERS = [
    'Employee Code',
    'First Name',
    'Last Name',
    'Email',
    'Mobile',
    'Branch Code',
    'Department Code',
    'Designation Code',
    'Date of Joining',
    'Basic Salary',
    'PAN',
    'Aadhaar',
    'UAN',
    'ESIC Number',
    'PF Eligible',
    'ESI Eligible',
    'Employment Status',
    'Bank Name',
    'Account Number',
    'IFSC',
]


def export_employees(queryset):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Employees'
    sheet.append(EXPORT_HEADERS)

    for employee in queryset.select_related('branch', 'department', 'designation'):
        sheet.append([
            employee.employee_code,
            employee.first_name,
            employee.last_name,
            employee.email,
            employee.mobile,
            employee.branch.code if employee.branch else '',
            employee.department.code if employee.department else '',
            employee.designation.code if employee.designation else '',
            employee.date_of_joining.isoformat() if employee.date_of_joining else '',
            float(employee.basic_salary),
            employee.pan,
            employee.aadhaar,
            employee.uan,
            employee.esic_number,
            'Yes' if employee.pf_eligible else 'No',
            'Yes' if employee.esi_eligible else 'No',
            employee.employment_status,
            employee.bank_name,
            employee.bank_account_number,
            employee.ifsc_code,
        ])

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="employees_export.xlsx"'
    return response


def export_employee_template():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Employees'
    sheet.append(EXPORT_HEADERS)
    sheet.append([
        '',
        'John',
        'Doe',
        'john@example.com',
        '9876543210',
        'HO',
        'FIN',
        'MGR',
        '2026-01-01',
        25000,
        'ABCDE1234F',
        '',
        '',
        '',
        'Yes',
        'No',
        'active',
        'State Bank',
        '1234567890',
        'SBIN0001234',
    ])

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="employee_import_template.xlsx"'
    return response


def import_employees(company, uploaded_file, user):
    workbook = load_workbook(uploaded_file, read_only=True, data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(min_row=2, values_only=True))

    from apps.company.models import Branch, Department, Designation

    created = 0
    errors = []

    for index, row in enumerate(rows, start=2):
        if not row or not any(row):
            continue
        try:
            code = str(row[0]).strip().upper() if row[0] else ''
            first_name = str(row[1]).strip() if row[1] else ''
            if not first_name:
                raise ValueError('First name is required.')

            branch = None
            department = None
            designation = None
            if row[5]:
                branch = Branch.objects.filter(company=company, code__iexact=str(row[5]).strip()).first()
            if row[6]:
                department = Department.objects.filter(company=company, code__iexact=str(row[6]).strip()).first()
            if row[7]:
                designation = Designation.objects.filter(company=company, code__iexact=str(row[7]).strip()).first()

            employee_kwargs = {
                'company': company,
                'branch': branch,
                'department': department,
                'designation': designation,
                'first_name': first_name,
                'last_name': str(row[2]).strip() if row[2] else '',
                'email': str(row[3]).strip() if row[3] else '',
                'mobile': str(row[4]).strip() if row[4] else '',
                'date_of_joining': row[8],
                'basic_salary': row[9] or 0,
                'pan': str(row[10]).strip().upper() if row[10] else '',
                'aadhaar': str(row[11]).strip() if row[11] else '',
                'uan': str(row[12]).strip() if row[12] else '',
                'esic_number': str(row[13]).strip() if row[13] else '',
                'pf_eligible': str(row[14]).strip().lower() in ('yes', 'true', '1'),
                'esi_eligible': str(row[15]).strip().lower() in ('yes', 'true', '1'),
                'employment_status': str(row[16]).strip() if row[16] else 'active',
                'bank_name': str(row[17]).strip() if row[17] else '',
                'bank_account_number': str(row[18]).strip() if row[18] else '',
                'ifsc_code': str(row[19]).strip().upper() if row[19] else '',
                'auto_generate_code': not bool(code),
                'created_by': user,
                'updated_by': user,
            }
            if code:
                employee_kwargs['employee_code'] = code

            Employee.objects.create(**employee_kwargs)
            created += 1
        except Exception as exc:
            errors.append(f'Row {index}: {exc}')

    return created, errors
