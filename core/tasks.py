from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import ApprovalTask


@shared_task
def send_approval_reminders():
    now = timezone.now()

    tasks = ApprovalTask.objects.filter(status='PENDING')

    for task in tasks:
        if task.snooze_until and task.snooze_until > now:
            continue

        interval = timedelta(hours=24)

        if task.urgency in ['HIGH', 'CRITICAL']:
            interval = timedelta(hours=2)

        if now - task.updated_at >= interval:
            print(
                f"Reminder: {task.approver.username} "
                f"has pending approval: {task.title}"
            )
