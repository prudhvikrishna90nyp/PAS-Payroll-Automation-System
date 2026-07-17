from django.urls import path

from . import views

app_name = 'attendance'

urlpatterns = [
    # Masters & tools before daily pk routes
    path('shifts/', views.ShiftListView.as_view(), name='shift_list'),
    path('shifts/add/', views.ShiftCreateView.as_view(), name='shift_add'),
    path('shifts/<int:pk>/', views.ShiftDetailView.as_view(), name='shift_detail'),
    path('shifts/<int:pk>/edit/', views.ShiftUpdateView.as_view(), name='shift_edit'),
    path('shifts/<int:pk>/archive/', views.ShiftArchiveView.as_view(), name='shift_archive'),

    path('holidays/', views.HolidayListView.as_view(), name='holiday_list'),
    path('holidays/add/', views.HolidayCreateView.as_view(), name='holiday_add'),
    path('holidays/<int:pk>/', views.HolidayDetailView.as_view(), name='holiday_detail'),
    path('holidays/<int:pk>/edit/', views.HolidayUpdateView.as_view(), name='holiday_edit'),
    path('holidays/<int:pk>/archive/', views.HolidayArchiveView.as_view(), name='holiday_archive'),

    path('periods/', views.PeriodListView.as_view(), name='period_list'),
    path('periods/add/', views.PeriodCreateView.as_view(), name='period_add'),
    path('periods/<int:pk>/', views.PeriodDetailView.as_view(), name='period_detail'),
    path('periods/<int:pk>/edit/', views.PeriodUpdateView.as_view(), name='period_edit'),
    path('periods/<int:pk>/transition/', views.PeriodTransitionView.as_view(), name='period_transition'),
    path('periods/<int:pk>/summaries/', views.PeriodGenerateSummaryView.as_view(), name='period_summaries'),
    path('periods/<int:pk>/delete/', views.PeriodDeleteView.as_view(), name='period_delete'),

    path('weekly-offs/', views.WeeklyOffListView.as_view(), name='weeklyoff_list'),
    path('weekly-offs/add/', views.WeeklyOffCreateView.as_view(), name='weeklyoff_add'),
    path('weekly-offs/<int:pk>/edit/', views.WeeklyOffUpdateView.as_view(), name='weeklyoff_edit'),
    path('weekly-offs/<int:pk>/delete/', views.WeeklyOffDeleteView.as_view(), name='weeklyoff_delete'),

    path('shift-assignments/', views.ShiftAssignmentListView.as_view(), name='shiftassignment_list'),
    path('shift-assignments/add/', views.ShiftAssignmentCreateView.as_view(), name='shiftassignment_add'),

    path('import/', views.AttendanceImportView.as_view(), name='attendance_import'),
    path('export/', views.AttendanceExportView.as_view(), name='attendance_export'),
    path('reports/', views.AttendanceReportIndexView.as_view(), name='report_index'),
    path('reports/<str:report_type>/', views.AttendanceReportDownloadView.as_view(), name='report_download'),

    path('', views.AttendanceListView.as_view(), name='attendance_list'),
    path('add/', views.AttendanceCreateView.as_view(), name='attendance_add'),
    path('<int:pk>/', views.AttendanceDetailView.as_view(), name='attendance_detail'),
    path('<int:pk>/edit/', views.AttendanceUpdateView.as_view(), name='attendance_edit'),
    path('<int:pk>/delete/', views.AttendanceDeleteView.as_view(), name='attendance_delete'),
]
