from django.contrib import admin
from .models import Organization, Team, User, ApprovalTask
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'domain', 'created_at')
@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization')
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'organization', 'team')
    list_filter = ('role', 'organization')
@admin.register(ApprovalTask)
class ApprovalTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'approver', 'created_at')
    readonly_fields = ()  # temporarily allow edit
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('task', 'action', 'performed_by', 'timestamp')
    list_filter = ('action',)
