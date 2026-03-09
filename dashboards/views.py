from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from core.models import User


# ──────────────────────────────────────────────────────────────────────────────
# HELPER: Create Notification
# ──────────────────────────────────────────────────────────────────────────────

def _notify(user, title, message, notif_type='system', link=''):
    from services.models import Notification
    try:
        Notification.objects.create(user=user, title=title, message=message, notif_type=notif_type, link=link)
    except Exception:
        pass


def _send_email(subject, body, to_email):
    from django.core.mail import send_mail
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email], fail_silently=True)
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
# DASHBOARDS
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def owner_dashboard(request):
    from services.models import Booking, Service
    from django.db.models import Sum, Count
    from django.utils import timezone
    import json
    import datetime

    bookings = Booking.objects.filter(provider=request.user).select_related('service', 'customer').order_by('-booking_date')
    completed = bookings.filter(status='Completed')
    total_earnings = completed.aggregate(total=Sum('service__base_price'))['total'] or 0

    # Monthly earnings for Chart.js (last 6 months)
    today = timezone.now().date()
    month_labels = []
    month_earnings = []
    month_bookings_count = []
    for i in range(5, -1, -1):
        month_date = today.replace(day=1) - datetime.timedelta(days=i * 30)
        label = month_date.strftime('%b %Y')
        month_labels.append(label)
        month_qs = completed.filter(
            booking_date__year=month_date.year,
            booking_date__month=month_date.month,
        )
        earn = month_qs.aggregate(total=Sum('service__base_price'))['total'] or 0
        month_earnings.append(float(earn))
        month_bookings_count.append(bookings.filter(
            booking_date__year=month_date.year,
            booking_date__month=month_date.month,
        ).count())

    # Unread notifications count
    from services.models import Notification
    unread_notifs = Notification.objects.filter(user=request.user, is_read=False).count()

    context = {
        'total_bookings':     bookings.count(),
        'pending_bookings':   bookings.filter(status='Pending').count(),
        'completed_bookings': completed.count(),
        'total_earnings':     total_earnings,
        'recent_bookings':    bookings[:8],
        'month_labels':       json.dumps(month_labels),
        'month_earnings':     json.dumps(month_earnings),
        'month_bookings':     json.dumps(month_bookings_count),
        'unread_notifs':      unread_notifs,
    }
    return render(request, 'dashboards/owner.html', context)


@login_required
def user_dashboard(request):
    from services.models import Booking, Wishlist, Notification
    bookings = Booking.objects.filter(customer=request.user).select_related('service').order_by('-booking_date')
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('service__category')
    unread_notifs = Notification.objects.filter(user=request.user, is_read=False).count()
    context = {
        'total_bookings':     bookings.count(),
        'pending_bookings':   bookings.filter(status='Pending').count(),
        'completed_bookings': bookings.filter(status='Completed').count(),
        'recent_bookings':    bookings[:5],
        'wishlist_items':     wishlist_items,
        'unread_notifs':      unread_notifs,
    }
    return render(request, 'dashboards/user.html', context)


@login_required
def admin_dashboard(request):
    from services.models import Service, Booking
    from django.db.models import Sum, Count
    from django.utils import timezone
    import json
    import datetime

    pending_admins  = User.objects.filter(role='admin', is_approved=False).order_by('-date_joined')
    recent_users    = User.objects.order_by('-date_joined')[:8]
    recent_bookings = Booking.objects.select_related('service', 'customer').order_by('-booking_date')[:8]

    # User growth last 6 months
    today = timezone.now().date()
    month_labels = []
    user_growth = []
    booking_growth = []
    for i in range(5, -1, -1):
        month_date = today.replace(day=1) - datetime.timedelta(days=i * 30)
        month_labels.append(month_date.strftime('%b %Y'))
        user_growth.append(User.objects.filter(
            date_joined__year=month_date.year,
            date_joined__month=month_date.month,
        ).count())
        booking_growth.append(Booking.objects.filter(
            booking_date__year=month_date.year,
            booking_date__month=month_date.month,
        ).count())

    # Top services by booking count
    top_services = Service.objects.annotate(booking_count=Count('bookings')).order_by('-booking_count')[:5]
    top_service_names  = json.dumps([s.name for s in top_services])
    top_service_counts = json.dumps([s.booking_count for s in top_services])

    context = {
        'total_users':        User.objects.filter(role='user').count(),
        'total_owners':       User.objects.filter(role='owner').count(),
        'total_services':     Service.objects.count(),
        'total_bookings':     Booking.objects.count(),
        'pending_bookings':   Booking.objects.filter(status='Pending').count(),
        'pending_admins':     pending_admins,
        'recent_users':       recent_users,
        'recent_bookings':    recent_bookings,
        'month_labels':       json.dumps(month_labels),
        'user_growth':        json.dumps(user_growth),
        'booking_growth':     json.dumps(booking_growth),
        'top_service_names':  top_service_names,
        'top_service_counts': top_service_counts,
    }
    return render(request, 'dashboards/admin.html', context)


# ──────────────────────────────────────────────────────────────────────────────
# ADMIN: Approve / Reject admin accounts
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def approve_admin(request, user_id):
    if request.user.role != 'admin' or not request.user.is_approved:
        return redirect('home')
    user = get_object_or_404(User, id=user_id, role='admin', is_approved=False)
    user.is_approved = True
    user.save()
    _send_email(
        '✅ Your Admin Account Has Been Approved – LocalServices',
        f"Hi {user.name},\n\nYour admin account has been approved.\nLogin: http://127.0.0.1:8000/core/login/\n\n— LocalServices Team",
        user.email,
    )
    messages.success(request, f"✅ {user.name}'s admin account has been approved.")
    return redirect('dashboards:admin')


@login_required
def reject_admin(request, user_id):
    if request.user.role != 'admin' or not request.user.is_approved:
        return redirect('home')
    user = get_object_or_404(User, id=user_id, role='admin', is_approved=False)
    name, email = user.name, user.email
    user.delete()
    _send_email(
        '❌ Admin Request Rejected – LocalServices',
        f"Hi {name},\n\nYour admin request has been rejected.\n\n— LocalServices Team",
        email,
    )
    messages.error(request, f"❌ {name}'s admin request has been rejected.")
    return redirect('dashboards:admin')


# ──────────────────────────────────────────────────────────────────────────────
# BOOKING ACTIONS
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def cancel_booking(request, booking_id):
    from services.models import Booking
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)
    if booking.status == 'Pending':
        booking.status = 'Cancelled'
        booking.save()
        if booking.provider:
            _notify(booking.provider, 'Booking Cancelled',
                    f'{request.user.name} cancelled booking #{booking.id} for "{booking.service.name}".',
                    'booking', '/dashboards/owner/')
        messages.success(request, f'Booking #{booking.id} has been cancelled.')
    else:
        messages.error(request, 'Only pending bookings can be cancelled.')
    return redirect('dashboards:user')


@login_required
def confirm_booking(request, booking_id):
    """Provider approves a pending booking."""
    from services.models import Booking
    booking = get_object_or_404(Booking, id=booking_id)
    if request.user.role != 'owner':
        messages.error(request, 'Only providers can confirm bookings.')
        return redirect('dashboards:owner')
    if booking.status == 'Pending':
        booking.provider = request.user
        booking.status = 'Confirmed'
        booking.save()
        # Notify customer
        _notify(booking.customer, '✅ Booking Confirmed!',
                f'Your booking for "{booking.service.name}" on {booking.scheduled_date} has been confirmed.',
                'booking', '/dashboards/user/')
        _send_email(
            f'✅ Booking Confirmed – {booking.service.name}',
            f"Hi {booking.customer.name},\n\nYour booking for \"{booking.service.name}\" on {booking.scheduled_date} has been confirmed by the provider.\n\nYou can now pay online:\nhttp://127.0.0.1:8000/services/payment/{booking.id}/\n\n— LocalServices Team",
            booking.customer.email,
        )
        messages.success(request, f'Booking #{booking.id} confirmed!')
    else:
        messages.error(request, 'Only pending bookings can be confirmed.')
    return redirect('dashboards:owner')


@login_required
def reject_booking(request, booking_id):
    """Provider rejects a pending booking."""
    from services.models import Booking
    booking = get_object_or_404(Booking, id=booking_id)
    if request.user.role != 'owner':
        messages.error(request, 'Only providers can reject bookings.')
        return redirect('dashboards:owner')
    if booking.status == 'Pending':
        booking.status = 'Rejected'
        booking.save()
        _notify(booking.customer, '❌ Booking Rejected',
                f'Your booking for "{booking.service.name}" on {booking.scheduled_date} was rejected by the provider.',
                'booking', '/dashboards/user/')
        _send_email(
            f'❌ Booking Rejected – {booking.service.name}',
            f"Hi {booking.customer.name},\n\nUnfortunately your booking for \"{booking.service.name}\" has been rejected.\nYou can search for other providers.\n\n— LocalServices Team",
            booking.customer.email,
        )
        messages.warning(request, f'Booking #{booking.id} has been rejected.')
    else:
        messages.error(request, 'Only pending bookings can be rejected.')
    return redirect('dashboards:owner')


@login_required
def complete_booking(request, booking_id):
    from services.models import Booking
    booking = get_object_or_404(Booking, id=booking_id, provider=request.user)
    if booking.status == 'Confirmed':
        booking.status = 'Completed'
        booking.save()
        _notify(booking.customer, '🎉 Service Completed',
                f'Your "{booking.service.name}" service has been marked as completed. Please leave a review!',
                'booking', f'/dashboards/booking/{booking.id}/review/')
        messages.success(request, f'Booking #{booking.id} marked as completed!')
    else:
        messages.error(request, 'Only confirmed bookings can be marked complete.')
    return redirect('dashboards:owner')


@login_required
def admin_update_booking(request, booking_id):
    from services.models import Booking
    if request.user.role != 'admin':
        return redirect('home')
    booking = get_object_or_404(Booking, id=booking_id)
    new_status = request.POST.get('status')
    valid = [s[0] for s in Booking.STATUS_CHOICES]
    if new_status in valid:
        booking.status = new_status
        booking.save()
        messages.success(request, f'Booking #{booking.id} status updated to {new_status}.')
    else:
        messages.error(request, 'Invalid status value.')
    return redirect('dashboards:admin')


# ──────────────────────────────────────────────────────────────────────────────
# REVIEWS
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def leave_review(request, booking_id):
    from services.models import Booking, Review
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user, status='Completed')
    if hasattr(booking, 'review'):
        messages.info(request, 'You have already reviewed this booking.')
        return redirect('dashboards:user')
    if request.method == 'POST':
        try:
            rating  = int(request.POST.get('rating', 0))
            comment = request.POST.get('comment', '').strip()
            if rating < 1 or rating > 5:
                messages.error(request, 'Please select a rating between 1 and 5.')
            else:
                Review.objects.create(booking=booking, rating=rating, comment=comment)
                messages.success(request, f'Thank you! Your review for "{booking.service.name}" has been saved.')
                return redirect('dashboards:user')
        except (ValueError, TypeError):
            messages.error(request, 'Invalid rating value.')
    return render(request, 'dashboards/review.html', {'booking': booking})


# ──────────────────────────────────────────────────────────────────────────────
# PROVIDER SERVICE MANAGEMENT
# ──────────────────────────────────────────────────────────────────────────────

def _require_owner(request):
    return request.user.is_authenticated and request.user.role == 'owner'


@login_required
def provider_services(request):
    if not _require_owner(request):
        return redirect('home')
    from services.models import Service, Category
    my_services = Service.objects.filter(owner=request.user).select_related('category').order_by('-id')
    categories  = Category.objects.all()
    return render(request, 'dashboards/provider_services.html', {
        'my_services': my_services,
        'categories': categories,
    })


@login_required
def add_service(request):
    if not _require_owner(request):
        return redirect('home')
    from services.models import Service, Category
    categories = Category.objects.all()
    if request.method == 'POST':
        name        = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        base_price  = request.POST.get('base_price', '').strip()
        category_id = request.POST.get('category', '')
        latitude    = request.POST.get('latitude', '') or None
        longitude   = request.POST.get('longitude', '') or None
        if not name or not base_price or not category_id:
            messages.error(request, 'Name, price, and category are required.')
        else:
            try:
                category = Category.objects.get(id=category_id)
                service = Service.objects.create(
                    owner=request.user,
                    category=category,
                    name=name,
                    description=description,
                    base_price=base_price,
                    latitude=latitude,
                    longitude=longitude,
                )
                if 'image' in request.FILES:
                    service.image = request.FILES['image']
                    service.save()
                messages.success(request, f'Service "{name}" added successfully!')
                return redirect('dashboards:provider_services')
            except (Category.DoesNotExist, ValueError) as e:
                messages.error(request, f'Error: {e}')
    return render(request, 'dashboards/service_form.html', {'categories': categories, 'action': 'Add'})


@login_required
def edit_service(request, service_id):
    if not _require_owner(request):
        return redirect('home')
    from services.models import Service, Category
    service    = get_object_or_404(Service, id=service_id, owner=request.user)
    categories = Category.objects.all()
    if request.method == 'POST':
        name        = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        base_price  = request.POST.get('base_price', '').strip()
        category_id = request.POST.get('category', '')
        is_active   = request.POST.get('is_active') == 'on'
        latitude    = request.POST.get('latitude', '') or None
        longitude   = request.POST.get('longitude', '') or None
        if not name or not base_price or not category_id:
            messages.error(request, 'Name, price, and category are required.')
        else:
            try:
                service.name        = name
                service.description = description
                service.base_price  = base_price
                service.category    = Category.objects.get(id=category_id)
                service.is_active   = is_active
                service.latitude    = latitude
                service.longitude   = longitude
                if 'image' in request.FILES:
                    service.image = request.FILES['image']
                service.save()
                messages.success(request, f'Service "{name}" updated!')
                return redirect('dashboards:provider_services')
            except (Category.DoesNotExist, ValueError) as e:
                messages.error(request, f'Error: {e}')
    return render(request, 'dashboards/service_form.html', {
        'service': service, 'categories': categories, 'action': 'Edit'
    })


@login_required
def delete_service(request, service_id):
    if not _require_owner(request):
        return redirect('home')
    from services.models import Service
    service = get_object_or_404(Service, id=service_id, owner=request.user)
    if request.method == 'POST':
        name = service.name
        service.delete()
        messages.success(request, f'Service "{name}" deleted.')
    return redirect('dashboards:provider_services')


# ──────────────────────────────────────────────────────────────────────────────
# PROVIDER EARNINGS
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def provider_earnings(request):
    if not _require_owner(request):
        return redirect('home')
    from services.models import Booking
    from django.db.models import Sum
    from django.utils import timezone
    import datetime

    all_bookings = Booking.objects.filter(provider=request.user, status='Completed').select_related('service', 'customer').order_by('-booking_date')
    total_earnings = all_bookings.aggregate(total=Sum('service__base_price'))['total'] or 0
    today = timezone.now().date()
    week_start  = today - datetime.timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    week_earnings  = all_bookings.filter(booking_date__date__gte=week_start).aggregate(total=Sum('service__base_price'))['total'] or 0
    month_earnings = all_bookings.filter(booking_date__date__gte=month_start).aggregate(total=Sum('service__base_price'))['total'] or 0
    return render(request, 'dashboards/earnings.html', {
        'completed_bookings': all_bookings,
        'total_earnings':     total_earnings,
        'week_earnings':      week_earnings,
        'month_earnings':     month_earnings,
    })


# ──────────────────────────────────────────────────────────────────────────────
# WISHLIST
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def toggle_wishlist(request, service_id):
    from services.models import Service, Wishlist
    service = get_object_or_404(Service, id=service_id)
    obj, created = Wishlist.objects.get_or_create(user=request.user, service=service)
    if not created:
        obj.delete()
        is_wishlisted = False
        msg = 'Removed from wishlist'
    else:
        is_wishlisted = True
        msg = 'Added to wishlist!'
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'is_wishlisted': is_wishlisted, 'message': msg})
    messages.success(request, msg)
    return redirect(request.META.get('HTTP_REFERER', 'services:list'))


# ──────────────────────────────────────────────────────────────────────────────
# LIVE CHAT
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def inbox_view(request):
    """Show all unique conversation partners."""
    from services.models import ChatMessage
    from django.db.models import Q, Max

    # Get all users this user has chatted with
    sent_to = ChatMessage.objects.filter(sender=request.user).values_list('receiver_id', flat=True)
    received_from = ChatMessage.objects.filter(receiver=request.user).values_list('sender_id', flat=True)
    partner_ids = set(list(sent_to) + list(received_from))
    partners = User.objects.filter(id__in=partner_ids)

    conversations = []
    for partner in partners:
        last_msg = ChatMessage.objects.filter(
            Q(sender=request.user, receiver=partner) | Q(sender=partner, receiver=request.user)
        ).last()
        unread = ChatMessage.objects.filter(sender=partner, receiver=request.user, is_read=False).count()
        conversations.append({'partner': partner, 'last_msg': last_msg, 'unread': unread})

    conversations.sort(key=lambda x: x['last_msg'].timestamp if x['last_msg'] else 0, reverse=True)
    return render(request, 'dashboards/inbox.html', {'conversations': conversations})


@login_required
def chat_view(request, other_user_id):
    """Render real-time chat page between current user and other user."""
    from services.models import ChatMessage
    from django.db.models import Q

    other_user = get_object_or_404(User, id=other_user_id)
    # Mark all incoming messages as read
    ChatMessage.objects.filter(sender=other_user, receiver=request.user, is_read=False).update(is_read=True)

    messages_qs = ChatMessage.objects.filter(
        Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user)
    ).order_by('timestamp')

    return render(request, 'dashboards/chat.html', {
        'other_user': other_user,
        'messages': messages_qs,
    })


@require_POST
@login_required
def send_message(request):
    from services.models import ChatMessage
    receiver_id = request.POST.get('receiver_id')
    message_text = request.POST.get('message', '').strip()
    if not receiver_id or not message_text:
        return JsonResponse({'error': 'Missing data'}, status=400)
    receiver = get_object_or_404(User, id=receiver_id)
    msg = ChatMessage.objects.create(
        sender=request.user,
        receiver=receiver,
        message=message_text,
    )
    # Create in-app notification for receiver
    _notify(receiver, f'New message from {request.user.name}',
            message_text[:100], 'message', f'/dashboards/chat/{request.user.id}/')
    return JsonResponse({
        'id': msg.id,
        'sender': request.user.name,
        'message': msg.message,
        'timestamp': msg.timestamp.strftime('%H:%M'),
        'is_mine': True,
    })


@login_required
def get_messages(request, other_user_id):
    """Poll for messages — returns JSON list."""
    from services.models import ChatMessage
    from django.db.models import Q

    other_user = get_object_or_404(User, id=other_user_id)
    since_id = request.GET.get('since', 0)

    msgs = ChatMessage.objects.filter(
        Q(sender=request.user, receiver=other_user) | Q(sender=other_user, receiver=request.user)
    ).filter(id__gt=since_id).order_by('timestamp')

    # Mark received as read
    msgs.filter(sender=other_user, receiver=request.user).update(is_read=True)

    data = [{
        'id': m.id,
        'sender': m.sender.name,
        'message': m.message,
        'timestamp': m.timestamp.strftime('%H:%M'),
        'is_mine': m.sender_id == request.user.id,
    } for m in msgs]
    return JsonResponse({'messages': data})


# ──────────────────────────────────────────────────────────────────────────────
# NOTIFICATIONS
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def notifications_view(request):
    from services.models import Notification
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]
    # Mark all as read when opened
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, 'dashboards/notifications.html', {'notifications': notifs})


@login_required
def mark_notification_read(request, notif_id):
    from services.models import Notification
    notif = get_object_or_404(Notification, id=notif_id, user=request.user)
    notif.is_read = True
    notif.save()
    if notif.link:
        return redirect(notif.link)
    return redirect('dashboards:notifications')


@login_required
def notifications_count(request):
    """AJAX endpoint: returns unread count."""
    from services.models import Notification
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})


# ──────────────────────────────────────────────────────────────────────────────
# PROVIDER CALENDAR
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def provider_calendar(request):
    """Provider manages their availability calendar."""
    if not _require_owner(request):
        return redirect('home')
    from services.models import ProviderAvailability
    from django.utils import timezone
    import json

    today = timezone.now().date()
    slots = ProviderAvailability.objects.filter(provider=request.user, date__gte=today).order_by('date', 'start_time')

    if request.method == 'POST':
        date_str   = request.POST.get('date', '')
        start_time = request.POST.get('start_time', '')
        end_time   = request.POST.get('end_time', '')
        if date_str and start_time and end_time:
            try:
                ProviderAvailability.objects.create(
                    provider=request.user,
                    date=date_str,
                    start_time=start_time,
                    end_time=end_time,
                    is_available=True,
                )
                messages.success(request, f'Availability slot added for {date_str}.')
            except Exception as e:
                messages.error(request, f'Error: {e}')
        else:
            messages.error(request, 'Please fill in all fields.')
        return redirect('dashboards:provider_calendar')

    # Prepare calendar data for JS
    slots_json = json.dumps([{
        'id': s.id,
        'date': str(s.date),
        'start': s.start_time.strftime('%H:%M'),
        'end': s.end_time.strftime('%H:%M'),
    } for s in slots])

    return render(request, 'dashboards/calendar.html', {
        'slots': slots,
        'slots_json': slots_json,
        'today': today,
    })


@login_required
def delete_availability(request, slot_id):
    if not _require_owner(request):
        return redirect('home')
    from services.models import ProviderAvailability
    slot = get_object_or_404(ProviderAvailability, id=slot_id, provider=request.user)
    slot.delete()
    messages.success(request, 'Availability slot removed.')
    return redirect('dashboards:provider_calendar')
