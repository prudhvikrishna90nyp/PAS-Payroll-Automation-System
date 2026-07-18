from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        'login/',
        RedirectView.as_view(url='/admin/login/', query_string=True, permanent=False),
    ),
    path('', include('apps.dashboard.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('clients/', include('apps.clients.urls')),
    path('companies/', include('apps.company.urls')),
    path('', include('apps.company.organisation_urls')),
    path('employees/', include('apps.employee.urls')),
    path('attendance/', include('apps.attendance.urls')),
    path('payroll/', include('apps.payroll.urls')),
    path('compliance/', include('apps.compliance.urls')),
    path('reports/', include('apps.reports.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
