from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from core.models import ApprovalTask, AuditLog, User
from core.utils import send_notification_email


class Command(BaseCommand):
    help = "Automated reminder and escalation engine for approvals"

    def handle(self, *args, **kwargs):
        now = timezone.now()

        # STEP 1: Get all pending approvals
        pending_tasks = ApprovalTask.objects.filter(status="PENDING")

        for task in pending_tasks:

            # ----------------------------------------
            # STEP 2: Skip snoozed tasks
            # ----------------------------------------
            if task.snooze_until and task.snooze_until > now:
                continue

            # ----------------------------------------
            # STEP 3: Determine reminder interval
            # ----------------------------------------
            if task.urgency == "CRITICAL":
                reminder_interval = timedelta(hours=2)
            elif task.urgency == "HIGH":
                reminder_interval = timedelta(hours=4)
            elif task.urgency == "NORMAL":
                reminder_interval = timedelta(hours=12)
            else:
                reminder_interval = timedelta(hours=24)

            # ----------------------------------------
            # STEP 4: Check if reminder needed
            # ----------------------------------------
            last_action = AuditLog.objects.filter(
                task=task,
                action="REMINDER"
            ).order_by("-timestamp").first()

            last_reminder_time = last_action.timestamp if last_action else task.created_at

            if now - last_reminder_time >= reminder_interval:
                self.send_reminder(task)
                continue  # Avoid escalation on same cycle

            # ----------------------------------------
            # STEP 5: Escalation check (48 hours)
            # ----------------------------------------
            if now - task.created_at >= timedelta(hours=48):
                self.escalate(task)

    # =====================================================
    # REMINDER LOGIC
    # =====================================================
    def send_reminder(self, task):
        AuditLog.objects.create(
            task=task,
            action="REMINDER",
            performed_by=None,
            remarks=f"Automated reminder sent to {task.approver.username}"
        )

        if task.approver.email:
            send_notification_email(
                subject="Approval Reminder",
                message=f"""
Hello {task.approver.username},

This is a reminder for the pending approval:

Title: {task.title}
Requested by: {task.requester.username}
Urgency: {task.urgency}

Please take action.
""",
                recipient_list=[task.approver.email]
            )

        self.stdout.write(
            self.style.WARNING(
                f"[REMINDER] Sent for task '{task.title}'"
            )
        )

    # =====================================================
    # ESCALATION LOGIC
    # =====================================================
    def escalate(self, task):
        already_escalated = AuditLog.objects.filter(
            task=task,
            action="ESCALATED"
        ).exists()

        if already_escalated:
            return

        admin = User.objects.filter(role="ADMIN").first()
        if not admin:
            return

        task.approver = admin
        task.save()

        AuditLog.objects.create(
            task=task,
            action="ESCALATED",
            performed_by=None,
            remarks=f"Auto-escalated to ADMIN ({admin.username})"
        )

        # Notify admin
        if admin.email:
            send_notification_email(
                subject="Approval Escalated",
                message=f"""
Hello {admin.username},

An approval has been escalated to you due to delay.

Title: {task.title}
Original approver did not respond within SLA.
""",
                recipient_list=[admin.email]
            )

        self.stdout.write(
            self.style.ERROR(
                f"[ESCALATED] Task '{task.title}' escalated to ADMIN"
            )
        )
