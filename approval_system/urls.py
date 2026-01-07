from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),   # ✅ FIX
    path('dashboard/', views.dashboard, name='dashboard'),

    path('create/', views.create_approval, name='create_approval'),
    path('approve/<int:task_id>/', views.approve_task, name='approve'),
    path('reject/<int:task_id>/', views.reject_task, name='reject'),
    path('snooze/<int:task_id>/<int:hours>/', views.snooze_task, name='snooze'),
    path('audit/<int:task_id>/', views.audit_timeline, name='audit'),
]
