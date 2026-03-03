from django.urls import path
from . import views

app_name = 'dashboards'

urlpatterns = [
    path('owner/',                 views.owner_dashboard, name='owner'),
    path('user/',                  views.user_dashboard,  name='user'),
    path('admin/',                 views.admin_dashboard, name='admin'),
    path('admin/approve/<int:user_id>/', views.approve_admin, name='approve_admin'),
    path('admin/reject/<int:user_id>/',  views.reject_admin,  name='reject_admin'),
]
