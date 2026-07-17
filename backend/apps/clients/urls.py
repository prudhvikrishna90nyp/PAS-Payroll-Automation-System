from django.urls import path

from .views import (
    ClientArchiveView,
    ClientCreateView,
    ClientDetailView,
    ClientListView,
    ClientRestoreView,
    ClientUpdateView,
)

app_name = 'clients'

urlpatterns = [
    path('', ClientListView.as_view(), name='client_list'),
    path('add/', ClientCreateView.as_view(), name='client_add'),
    path('<int:pk>/', ClientDetailView.as_view(), name='client_detail'),
    path('<int:pk>/edit/', ClientUpdateView.as_view(), name='client_edit'),
    path('<int:pk>/archive/', ClientArchiveView.as_view(), name='client_archive'),
    path('<int:pk>/restore/', ClientRestoreView.as_view(), name='client_restore'),
]
