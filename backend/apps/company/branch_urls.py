from django.urls import path

from . import views

urlpatterns = [
    path('', views.branch_list, name='branch_list'),
    path('add/', views.branch_create, name='branch_create'),
    path('<int:pk>/edit/', views.branch_update, name='branch_update'),
    path('<int:pk>/delete/', views.branch_delete, name='branch_delete'),
]
