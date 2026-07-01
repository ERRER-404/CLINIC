from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.DashboardStatsView.as_view(), name='dashboard_stats'),
    path('revenue/', views.RevenueChartView.as_view(), name='revenue_chart'),
    path('top-treatments/', views.TopTreatmentsView.as_view(), name='top_treatments'),
    path('patient-growth/', views.PatientGrowthView.as_view(), name='patient_growth'),
]
