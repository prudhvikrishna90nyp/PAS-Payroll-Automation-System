from django.urls import path

from . import views

urlpatterns = [
    path('companies/', views.company_list, name='company_list'),
    path('companies/add/', views.company_create, name='company_create'),
    path('companies/<int:pk>/edit/', views.company_update, name='company_update'),
    path('companies/<int:pk>/delete/', views.company_delete, name='company_delete'),

    path('branches/', views.branch_list, name='branch_list'),
    path('branches/add/', views.branch_create, name='branch_create'),
    path('branches/<int:pk>/edit/', views.branch_update, name='branch_update'),
    path('branches/<int:pk>/delete/', views.branch_delete, name='branch_delete'),
]
