from django.contrib import admin
from .models import ReporterProfile

@admin.register(ReporterProfile)
class ReporterProfileAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'reporter_status', 'kyc_status']
    search_fields = ['id', 'user', 'reporter_status', 'kyc_status']
    list_filter = ['id', 'user', 'reporter_status', 'kyc_status']
