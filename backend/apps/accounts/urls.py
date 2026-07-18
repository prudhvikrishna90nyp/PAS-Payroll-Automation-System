from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    # Docs and common expectation use /accounts/login/; auth is Django admin login.
    path(
        'login/',
        RedirectView.as_view(url='/admin/login/', query_string=True, permanent=False),
        name='login',
    ),
    path('profile/', views.profile, name='profile'),
]
