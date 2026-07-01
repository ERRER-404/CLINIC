from django.contrib import admin
from .models import Appointment, TimeSlot

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'treatment', 'date', 'time', 'status']
    list_filter = ['status', 'date', 'clinic']
    search_fields = ['patient__user__username', 'doctor__user__username']

@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'day_of_week', 'start_time', 'end_time', 'is_available']
    list_filter = ['day_of_week', 'is_available']
