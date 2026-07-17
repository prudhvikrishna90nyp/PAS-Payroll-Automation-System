from django.urls import path

from .views import (
    CompanyArchiveView,
    CompanyCreateView,
    CompanyDetailView,
    CompanyListView,
    CompanyRestoreView,
    CompanyUpdateView,
)

app_name = 'company'

urlpatterns = [
    path('', CompanyListView.as_view(), name='company_list'),
    path('add/', CompanyCreateView.as_view(), name='company_add'),
    path('<int:pk>/', CompanyDetailView.as_view(), name='company_detail'),
    path('<int:pk>/edit/', CompanyUpdateView.as_view(), name='company_edit'),
    path('<int:pk>/archive/', CompanyArchiveView.as_view(), name='company_archive'),
    path('<int:pk>/restore/', CompanyRestoreView.as_view(), name='company_restore'),
]
