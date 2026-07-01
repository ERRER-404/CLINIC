from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    # Auth
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profile
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/doctor/', views.DoctorProfileUpdateView.as_view(), name='doctor_profile_update'),
    path('profile/doctor/<int:doctor_id>/', views.DoctorProfileAssignView.as_view(), name='doctor_profile_assign'),
    path('profile/patient/', views.PatientProfileUpdateView.as_view(), name='patient_profile_update'),
    path('profile/clinic-manager/', views.ClinicManagerProfileUpdateView.as_view(), name='clinic_manager_profile_update'),
    path('profile/change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    
    # Admin
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    
    # Public
    path('doctors/', views.DoctorListView.as_view(), name='doctor_list'),
    
    # Clinic
    path('clinic-patients/', views.ClinicPatientsListView.as_view(), name='clinic_patients_list'),
    
    # Doctor
    path('doctor-patients/', views.DoctorPatientsView.as_view(), name='doctor_patients_list'),
]
