from django.urls import path
from . import views

app_name = 'dashboards'

urlpatterns = [
    # ── Dashboards ────────────────────────────────────────────────────────────
    path('owner/',        views.owner_dashboard,  name='owner'),
    path('user/',         views.user_dashboard,   name='user'),
    path('admin/',        views.admin_dashboard,  name='admin'),

    # ── Admin: approve/reject admin accounts ─────────────────────────────────
    path('admin/approve/<int:user_id>/', views.approve_admin, name='approve_admin'),
    path('admin/reject/<int:user_id>/',  views.reject_admin,  name='reject_admin'),

    # ── Booking actions ───────────────────────────────────────────────────────
    path('booking/<int:booking_id>/cancel/',   views.cancel_booking,        name='cancel_booking'),
    path('booking/<int:booking_id>/confirm/',  views.confirm_booking,       name='confirm_booking'),
    path('booking/<int:booking_id>/reject/',   views.reject_booking,        name='reject_booking'),
    path('booking/<int:booking_id>/complete/', views.complete_booking,      name='complete_booking'),
    path('booking/<int:booking_id>/status/',   views.admin_update_booking,  name='admin_update_booking'),
    path('booking/<int:booking_id>/review/',   views.leave_review,          name='leave_review'),

    # ── Provider features ─────────────────────────────────────────────────────
    path('provider/services/',                          views.provider_services,  name='provider_services'),
    path('provider/services/add/',                      views.add_service,        name='add_service'),
    path('provider/services/<int:service_id>/edit/',    views.edit_service,       name='edit_service'),
    path('provider/services/<int:service_id>/delete/',  views.delete_service,     name='delete_service'),
    path('provider/earnings/',                          views.provider_earnings,  name='provider_earnings'),
    path('provider/calendar/',                          views.provider_calendar,  name='provider_calendar'),
    path('provider/calendar/<int:slot_id>/delete/',     views.delete_availability, name='delete_availability'),

    # ── Wishlist ──────────────────────────────────────────────────────────────
    path('wishlist/toggle/<int:service_id>/', views.toggle_wishlist, name='toggle_wishlist'),

    # ── Chat / Inbox ──────────────────────────────────────────────────────────
    path('inbox/',                          views.inbox_view,    name='inbox'),
    path('chat/<int:other_user_id>/',       views.chat_view,     name='chat'),
    path('chat/send/',                      views.send_message,  name='send_message'),
    path('chat/messages/<int:other_user_id>/', views.get_messages, name='get_messages'),

    # ── Notifications ─────────────────────────────────────────────────────────
    path('notifications/',                        views.notifications_view,       name='notifications'),
    path('notifications/<int:notif_id>/read/',    views.mark_notification_read,   name='mark_notification_read'),
    path('notifications/count/',                  views.notifications_count,      name='notifications_count'),
]
