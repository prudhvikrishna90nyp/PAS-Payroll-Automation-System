from django.http import HttpResponse
from django.template.loader import render_to_string


def render_employee_register_pdf(employees, title='Employee Register', request=None):
    """Render an employee register PDF via WeasyPrint when system libs are available."""
    try:
        from weasyprint import HTML
    except (OSError, ImportError):
        return HttpResponse(
            'PDF generation requires WeasyPrint system libraries. '
            'On Windows, install GTK3 runtime: '
            'https://doc.courtbouillon.org/weasyprint/stable/first_steps.html',
            status=503,
        )

    html = render_to_string(
        'employee/employee_register_pdf.html',
        {
            'employees': employees,
            'title': title,
        },
        request=request,
    )
    base_url = request.build_absolute_uri('/') if request else None
    pdf = HTML(string=html, base_url=base_url).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    safe_title = title.lower().replace(' ', '_')
    response['Content-Disposition'] = f'attachment; filename="{safe_title}.pdf"'
    return response
