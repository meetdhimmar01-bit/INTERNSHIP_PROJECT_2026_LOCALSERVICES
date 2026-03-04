from django.urls import path
from . import views

app_name = 'dashboards'

urlpatterns = [
    path('owner/',                        views.owner_dashboard,      name='owner'),
    path('user/',                         views.user_dashboard,       name='user'),
    path('admin/',                        views.admin_dashboard,      name='admin'),
    path('admin/approve/<int:user_id>/',  views.approve_admin,        name='approve_admin'),
    path('admin/reject/<int:user_id>/',   views.reject_admin,         name='reject_admin'),
    # Booking actions
    path('booking/<int:booking_id>/cancel/',   views.cancel_booking,        name='cancel_booking'),
    path('booking/<int:booking_id>/confirm/',  views.confirm_booking,       name='confirm_booking'),
    path('booking/<int:booking_id>/complete/', views.complete_booking,      name='complete_booking'),
    path('booking/<int:booking_id>/status/',   views.admin_update_booking,  name='admin_update_booking'),
    path('booking/<int:booking_id>/review/',   views.leave_review,          name='leave_review'),
    # Provider features
    path('provider/services/',                 views.provider_services,     name='provider_services'),
    path('provider/services/add/',             views.add_service,           name='add_service'),
    path('provider/services/<int:service_id>/edit/',   views.edit_service,  name='edit_service'),
    path('provider/services/<int:service_id>/delete/', views.delete_service, name='delete_service'),
    path('provider/earnings/',                 views.provider_earnings,     name='provider_earnings'),
]
