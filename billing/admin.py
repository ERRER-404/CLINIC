from django.contrib import admin
from .models import Invoice

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['id', 'appointment', 'total', 'status', 'created_at', 'paid_at']
    list_filter = ['status']
