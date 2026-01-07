from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponseForbidden

from .models import ApprovalTask, AuditLog, User
from .utils import send_notification_email


# =========================================================
# AUTHENTICATION VIEWS
# =========================================================

def login_view(request):
    """
    Handles user login.
    Only this view is allowed to authenticate a user.
    """

    # If user already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard")

        # Authentication failed
        return render(request, "login.html", {
            "error": "Invalid username or password"
        })

    return render(request, "login.html")


@login_required
def logout_view(request):
    """
    Logs out the current user and clears session.
    """
    logout(request)
    return redirect("login")


# =========================================================
# DASHBOARD
# =========================================================

@login_required
def dashboard(request):
    """
    Main dashboard.
    Shows:
    1. Approvals assigned to the user (to act on)
    2. Approvals created by the user (tracking)
    3. SLA buckets for assigned approvals
    """

    user = request.user
    now = timezone.now()

    # ---------------------------------------------
    # Approvals ASSIGNED to this user (pending)
    # ---------------------------------------------
    assigned_tasks = ApprovalTask.objects.filter(
        approver=user,
        status="PENDING"
    )

    # ---------------------------------------------
    # Approvals CREATED by this user
    # ---------------------------------------------
    created_tasks = ApprovalTask.objects.filter(
        requester=user
    )

    # ---------------------------------------------
    # SLA BUCKET CALCULATION
    # ---------------------------------------------
    sla_green = []
    sla_yellow = []
    sla_red = []

    for task in assigned_tasks:
        hours_passed = (now - task.created_at).total_seconds() / 3600

        if hours_passed < 24:
            sla_green.append(task)
        elif hours_passed < 48:
            sla_yellow.append(task)
        else:
            sla_red.append(task)

    return render(request, "dashboard.html", {
        "user": user,
        "assigned_tasks": assigned_tasks,
        "created_tasks": created_tasks,
        "sla_green": sla_green,
        "sla_yellow": sla_yellow,
        "sla_red": sla_red,
    })


# =========================================================
# CREATE APPROVAL
# =========================================================

@login_required
def create_approval(request):
    """
    Allows any logged-in user (employee/manager/admin)
    to create an approval request.
    """

    if request.method == "POST":
        title = request.POST.get("title")
        urgency = request.POST.get("urgency")
        approver_id = request.POST.get("approver")

        # Validate approver
        approver = get_object_or_404(User, id=approver_id)

        # Create approval task
        approval = ApprovalTask.objects.create(
            title=title,
            requester=request.user,
            approver=approver,
            urgency=urgency,
            status="PENDING"
        )

        # Audit log
        AuditLog.objects.create(
            task=approval,
            action="CREATED",
            performed_by=request.user
        )

        # Email notification to approver
        if approver.email:
            send_notification_email(
                subject="New Approval Request",
                message=f"""
Hello {approver.username},

A new approval request has been created.

Title: {approval.title}
Requested by: {request.user.username}
Urgency: {approval.urgency}

Please log in to review.
""",
                recipient_list=[approver.email]
            )

        return redirect("dashboard")

    # Only MANAGER or ADMIN can be selected as approver
    approvers = User.objects.filter(role__in=["MANAGER", "ADMIN"])

    return render(request, "create_approval.html", {
        "approvers": approvers
    })


# =========================================================
# APPROVE TASK
# =========================================================

@login_required
def approve_task(request, task_id):
    """
    Allows the assigned approver to approve a task
    with an optional comment.
    """

    task = get_object_or_404(ApprovalTask, id=task_id)

    # Authorization check
    if task.approver != request.user:
        return HttpResponseForbidden("You are not authorized to approve this task")

    comment = request.POST.get("comment", "").strip()

    # Update task
    task.status = "APPROVED"
    task.updated_at = timezone.now()
    task.save()

    # Audit log
    AuditLog.objects.create(
        task=task,
        action="APPROVED",
        performed_by=request.user,
        remarks=comment if comment else "Approved without comment"
    )

    # Email requester
    if task.requester.email:
        send_notification_email(
            subject="Approval Approved",
            message=f"""
Hello {task.requester.username},

Your approval request "{task.title}" has been APPROVED.

Comment:
{comment if comment else "No comment provided"}
""",
            recipient_list=[task.requester.email]
        )

    return redirect("dashboard")


# =========================================================
# REJECT TASK
# =========================================================

@login_required
def reject_task(request, task_id):
    """
    Allows the assigned approver to reject a task.
    Rejection MUST include a reason.
    """

    task = get_object_or_404(ApprovalTask, id=task_id)

    # Authorization check
    if task.approver != request.user:
        return HttpResponseForbidden("You are not authorized to reject this task")

    comment = request.POST.get("comment", "").strip()

    if not comment:
        return HttpResponseForbidden("Rejection requires a reason")

    # Update task
    task.status = "REJECTED"
    task.updated_at = timezone.now()
    task.save()

    # Audit log
    AuditLog.objects.create(
        task=task,
        action="REJECTED",
        performed_by=request.user,
        remarks=comment
    )

    # Email requester
    if task.requester.email:
        send_notification_email(
            subject="Approval Rejected",
            message=f"""
Hello {task.requester.username},

Your approval request "{task.title}" has been REJECTED.

Reason:
{comment}
""",
            recipient_list=[task.requester.email]
        )

    return redirect("dashboard")


# =========================================================
# SNOOZE TASK
# =========================================================

@login_required
def snooze_task(request, task_id, hours):
    """
    Allows approver to snooze a task for N hours.
    Snoozed tasks are skipped by reminder job.
    """

    task = get_object_or_404(ApprovalTask, id=task_id)

    if task.approver != request.user:
        return HttpResponseForbidden("You are not authorized to snooze this task")

    task.snooze_until = timezone.now() + timezone.timedelta(hours=hours)
    task.save()

    AuditLog.objects.create(
        task=task,
        action="SNOOZED",
        performed_by=request.user,
        remarks=f"Snoozed for {hours} hours"
    )

    return redirect("dashboard")


# =========================================================
# AUDIT TIMELINE
# =========================================================

@login_required
def audit_timeline(request, task_id):
    """
    Shows full lifecycle of an approval.
    Visible to requester, approver, or admin only.
    """

    task = get_object_or_404(ApprovalTask, id=task_id)

    # Authorization
    if (
        request.user != task.requester and
        request.user != task.approver and
        request.user.role != "ADMIN"
    ):
        return HttpResponseForbidden("You are not allowed to view this audit")

    logs = AuditLog.objects.filter(task=task).order_by("timestamp")

    return render(request, "audit_timeline.html", {
        "task": task,
        "logs": logs
    })
