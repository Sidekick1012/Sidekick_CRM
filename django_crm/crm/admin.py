from django.contrib import admin
from .models import CRMSetting, Lead, Task, SaleReport, EmailTemplate, Campaign, CampaignLog, FollowupLog

@admin.register(CRMSetting)
class CRMSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value')

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('name', 'company', 'email', 'status', 'temperature', 'followup_date')
    list_filter = ('status', 'temperature', 'source')
    search_fields = ('name', 'company', 'email')

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'lead', 'priority', 'due_date', 'done')
    list_filter = ('priority', 'done', 'due_date')
    search_fields = ('title', 'description')

@admin.register(SaleReport)
class SaleReportAdmin(admin.ModelAdmin):
    list_display = ('client', 'category', 'amount', 'month_year')
    list_filter = ('category', 'month_year')
    search_fields = ('client', 'category', 'notes')

admin.site.register(EmailTemplate)
admin.site.register(Campaign)
admin.site.register(CampaignLog)
admin.site.register(FollowupLog)
