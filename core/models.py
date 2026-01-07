from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


# =========================================================
# ORGANIZATION
# =========================================================
class Organization(models.Model):
    """
    Represents a company / organization (e.g., BhaktiLink).
    """

    name = models.CharField(max_length=200)
    domain = models.CharField(max_length=100, unique=True)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name


# =========================================================
# TEAM
# =========================================================
class Team(models.Model):
    """
    Represents a team within an organization (e.g., Vishnu-12).
    """

    name = models.CharField(max_length=100)

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="teams"
    )

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


# =========================================================
# CUSTOM USER
# =========================================================
class User(AbstractUser):
    """
    Custom user model with role, organization, team and timezone.
    """

    ROLE_CHOICES = (
        ('EMPLOYEE', 'Employee'),
        ('MANAGER', 'Manager'),
        ('ADMIN', 'Admin'),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='EMPLOYEE'
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="users"
    )

    team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members"
    )

    timezone = models.CharField(
        max_length=50,
        default='Asia/Kolkata'
    )

    def __str__(self):
        return self.username


# =========================================================
# APPROVAL TASK
# =========================================================
class ApprovalTask(models.Model):
    """
    Core approval entity.
    One task = one approval request.
    """

    URGENCY_CHOICES = (
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('CRITICAL', 'Critical'),
    )

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    requester = models.ForeignKey(
        User,
        related_name='requested_tasks',
        on_delete=models.CASCADE
    )

    approver = models.ForeignKey(
        User,
        related_name='assigned_approvals',
        on_delete=models.CASCADE
    )

    urgency = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        default='MEDIUM'
    )

    # Reminder interval (minutes)
    # Default = 24 hours
    reminder_interval_minutes = models.PositiveIntegerField(default=1440)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )

    snooze_until = models.DateTimeField(
        null=True,
        blank=True
    )

    # Editable for testing & simulation
    created_at = models.DateTimeField(default=timezone.now)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['urgency']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.title} ({self.status})"


# =========================================================
# AUDIT LOG
# =========================================================
class AuditLog(models.Model):
    """
    Immutable event log for approvals.
    This is the proof layer of the system.
    """

    ACTION_CHOICES = (
        ('CREATED', 'Created'),
        ('REMINDER', 'Reminder Sent'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('SNOOZED', 'Snoozed'),
        ('ESCALATED', 'Escalated'),
    )

    task = models.ForeignKey(
        ApprovalTask,
        on_delete=models.CASCADE,
        related_name='audit_logs'
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES
    )

    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    timestamp = models.DateTimeField(auto_now_add=True)

    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.task.title} → {self.action}"
