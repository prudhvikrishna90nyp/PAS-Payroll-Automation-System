from django.urls import path

from .organisation_views import (
    BranchArchiveView,
    BranchCreateView,
    BranchDetailView,
    BranchListView,
    BranchRestoreView,
    BranchUpdateView,
    DepartmentArchiveView,
    DepartmentCreateView,
    DepartmentDetailView,
    DepartmentListView,
    DepartmentRestoreView,
    DepartmentUpdateView,
    DesignationArchiveView,
    DesignationCreateView,
    DesignationDetailView,
    DesignationListView,
    DesignationRestoreView,
    DesignationUpdateView,
)

app_name = 'organisation'

urlpatterns = [
    path('branches/', BranchListView.as_view(), name='branch_list'),
    path('branches/add/', BranchCreateView.as_view(), name='branch_add'),
    path('branches/<int:pk>/', BranchDetailView.as_view(), name='branch_detail'),
    path('branches/<int:pk>/edit/', BranchUpdateView.as_view(), name='branch_edit'),
    path('branches/<int:pk>/archive/', BranchArchiveView.as_view(), name='branch_archive'),
    path('branches/<int:pk>/restore/', BranchRestoreView.as_view(), name='branch_restore'),

    path('departments/', DepartmentListView.as_view(), name='department_list'),
    path('departments/add/', DepartmentCreateView.as_view(), name='department_add'),
    path('departments/<int:pk>/', DepartmentDetailView.as_view(), name='department_detail'),
    path('departments/<int:pk>/edit/', DepartmentUpdateView.as_view(), name='department_edit'),
    path('departments/<int:pk>/archive/', DepartmentArchiveView.as_view(), name='department_archive'),
    path('departments/<int:pk>/restore/', DepartmentRestoreView.as_view(), name='department_restore'),

    path('designations/', DesignationListView.as_view(), name='designation_list'),
    path('designations/add/', DesignationCreateView.as_view(), name='designation_add'),
    path('designations/<int:pk>/', DesignationDetailView.as_view(), name='designation_detail'),
    path('designations/<int:pk>/edit/', DesignationUpdateView.as_view(), name='designation_edit'),
    path('designations/<int:pk>/archive/', DesignationArchiveView.as_view(), name='designation_archive'),
    path('designations/<int:pk>/restore/', DesignationRestoreView.as_view(), name='designation_restore'),
]
