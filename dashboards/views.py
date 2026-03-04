from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.models import User


@login_required
def owner_dashboard(request):
    from services.models import Booking
    from django.db.models import Sum
    bookings = Booking.objects.filter(provider=request.user).select_related('service', 'customer').order_by('-booking_date')
    total_earnings = bookings.filter(status='Completed').aggregate(total=Sum('service__base_price'))['total'] or 0
    context = {
        'total_bookings':    bookings.count(),
        'pending_bookings':  bookings.filter(status='Pending').count(),
        'completed_bookings': bookings.filter(status='Completed').count(),
        'total_earnings':    total_earnings,
        'recent_bookings':   bookings[:8],
    }
    return render(request, 'dashboards/owner.html', context)


@login_required
def user_dashboard(request):
    from services.models import Booking
    bookings = Booking.objects.filter(customer=request.user).select_related('service').order_by('-booking_date')
    context = {
        'total_bookings':    bookings.count(),
        'pending_bookings':  bookings.filter(status='Pending').count(),
        'completed_bookings': bookings.filter(status='Completed').count(),
        'recent_bookings':   bookings[:5],
    }
    return render(request, 'dashboards/user.html', context)


@login_required
def admin_dashboard(request):
    from services.models import Service, Booking
    pending_admins = User.objects.filter(role='admin', is_approved=False).order_by('-date_joined')
    recent_users   = User.objects.order_by('-date_joined')[:8]
    recent_bookings = Booking.objects.select_related('service', 'customer').order_by('-booking_date')[:8]
    context = {
        'total_users':      User.objects.filter(role='user').count(),
        'total_owners':     User.objects.filter(role='owner').count(),
        'total_services':   Service.objects.count(),
        'total_bookings':   Booking.objects.count(),
        'pending_bookings': Booking.objects.filter(status='Pending').count(),
        'pending_admins':   pending_admins,
        'recent_users':     recent_users,
        'recent_bookings':  recent_bookings,
    }
    return render(request, 'dashboards/admin.html', context)


@login_required
def approve_admin(request, user_id):
    """Approve a pending admin account."""
    if request.user.role != 'admin' or not request.user.is_approved:
        return redirect('home')
    user = get_object_or_404(User, id=user_id, role='admin', is_approved=False)
    user.is_approved = True
    user.save()
    # Send approval notification email
    from django.core.mail import send_mail
    from django.conf import settings
    try:
        send_mail(
            '✅ Your Admin Account Has Been Approved – LocalServices',
            f"""Hi {user.name},

Great news! Your admin account on LocalServices Management has been approved.

  📧 Email : {user.email}
  🔑 Role  : Admin

You can now login at: http://127.0.0.1:8000/core/login/

— LocalServices Management Team
""",
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )
    except Exception:
        pass
    messages.success(request, f"✅ {user.name}'s admin account has been approved.")
    return redirect('dashboards:admin')


@login_required
def reject_admin(request, user_id):
    """Reject (delete) a pending admin account."""
    if request.user.role != 'admin' or not request.user.is_approved:
        return redirect('home')
    user = get_object_or_404(User, id=user_id, role='admin', is_approved=False)
    name = user.name
    email = user.email
    user.delete()
    # Send rejection notification email
    from django.core.mail import send_mail
    from django.conf import settings
    try:
        send_mail(
            '❌ Admin Request Rejected – LocalServices',
            f"""Hi {name},

Unfortunately, your Admin access request on LocalServices Management has been rejected.

If you believe this is a mistake, please contact support.

— LocalServices Management Team
""",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=True,
        )
    except Exception:
        pass
    messages.error(request, f"❌ {name}'s admin request has been rejected and account removed.")
    return redirect('dashboards:admin')


# ── Booking Actions ────────────────────────────────────────────────────────────

@login_required
def cancel_booking(request, booking_id):
    """User cancels their own pending booking."""
    from services.models import Booking
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)
    if booking.status == 'Pending':
        booking.status = 'Cancelled'
        booking.save()
        messages.success(request, f'Booking #{booking.id} has been cancelled.')
    else:
        messages.error(request, 'Only pending bookings can be cancelled.')
    return redirect('dashboards:user')


@login_required
def confirm_booking(request, booking_id):
    """Provider confirms (accepts) a pending booking assigned to them."""
    from services.models import Booking
    booking = get_object_or_404(Booking, id=booking_id)
    if request.user.role != 'owner':
        messages.error(request, 'Only providers can confirm bookings.')
        return redirect('dashboards:owner')
    if booking.status == 'Pending':
        booking.provider = request.user
        booking.status = 'Confirmed'
        booking.save()
        messages.success(request, f'Booking #{booking.id} confirmed!')
    else:
        messages.error(request, 'Only pending bookings can be confirmed.')
    return redirect('dashboards:owner')


@login_required
def complete_booking(request, booking_id):
    """Provider marks a confirmed booking as completed."""
    from services.models import Booking
    booking = get_object_or_404(Booking, id=booking_id, provider=request.user)
    if booking.status == 'Confirmed':
        booking.status = 'Completed'
        booking.save()
        messages.success(request, f'Booking #{booking.id} marked as completed!')
    else:
        messages.error(request, 'Only confirmed bookings can be marked complete.')
    return redirect('dashboards:owner')


@login_required
def admin_update_booking(request, booking_id):
    """Admin changes a booking's status to any value."""
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


# ── Reviews ────────────────────────────────────────────────────────────────────

@login_required
def leave_review(request, booking_id):
    """User leaves a star rating + comment for a completed booking."""
    from services.models import Booking, Review
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user, status='Completed')

    # Already reviewed?
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


# ── Provider Service Management ─────────────────────────────────────────────────

def _require_owner(request):
    """Return True if the request user is an approved owner, else redirect."""
    return request.user.is_authenticated and request.user.role == 'owner'


@login_required
def provider_services(request):
    """List + manage provider's own services."""
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
    """Provider adds a new service."""
    if not _require_owner(request):
        return redirect('home')
    from services.models import Service, Category
    categories = Category.objects.all()
    if request.method == 'POST':
        name        = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        base_price  = request.POST.get('base_price', '').strip()
        category_id = request.POST.get('category', '')
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
                )
                if 'image' in request.FILES:
                    service.image = request.FILES['image']
                    service.save()
                messages.success(request, f'Service "{name}" added successfully!')
                return redirect('dashboards:provider_services')
            except (Category.DoesNotExist, ValueError) as e:
                messages.error(request, f'Error: {e}')
    return render(request, 'dashboards/service_form.html', {
        'categories': categories,
        'action': 'Add',
    })


@login_required
def edit_service(request, service_id):
    """Provider edits their service."""
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
        if not name or not base_price or not category_id:
            messages.error(request, 'Name, price, and category are required.')
        else:
            try:
                service.name        = name
                service.description = description
                service.base_price  = base_price
                service.category    = Category.objects.get(id=category_id)
                service.is_active   = is_active
                if 'image' in request.FILES:
                    service.image = request.FILES['image']
                service.save()
                messages.success(request, f'Service "{name}" updated!')
                return redirect('dashboards:provider_services')
            except (Category.DoesNotExist, ValueError) as e:
                messages.error(request, f'Error: {e}')
    return render(request, 'dashboards/service_form.html', {
        'service': service,
        'categories': categories,
        'action': 'Edit',
    })


@login_required
def delete_service(request, service_id):
    """Provider deletes their service."""
    if not _require_owner(request):
        return redirect('home')
    from services.models import Service
    service = get_object_or_404(Service, id=service_id, owner=request.user)
    if request.method == 'POST':
        name = service.name
        service.delete()
        messages.success(request, f'Service "{name}" deleted.')
    return redirect('dashboards:provider_services')


# ── Provider Earnings ───────────────────────────────────────────────────────────

@login_required
def provider_earnings(request):
    """Detailed provider earnings breakdown."""
    if not _require_owner(request):
        return redirect('home')
    from services.models import Booking
    from django.db.models import Sum, Count
    from django.utils import timezone
    import datetime

    all_bookings = Booking.objects.filter(provider=request.user, status='Completed').select_related('service', 'customer').order_by('-booking_date')

    # Totals
    total_earnings = all_bookings.aggregate(total=Sum('service__base_price'))['total'] or 0

    today = timezone.now().date()
    # This week (Mon–Sun)
    week_start = today - datetime.timedelta(days=today.weekday())
    # This month
    month_start = today.replace(day=1)

    week_earnings  = all_bookings.filter(booking_date__date__gte=week_start).aggregate(total=Sum('service__base_price'))['total'] or 0
    month_earnings = all_bookings.filter(booking_date__date__gte=month_start).aggregate(total=Sum('service__base_price'))['total'] or 0

    return render(request, 'dashboards/earnings.html', {
        'completed_bookings': all_bookings,
        'total_earnings':     total_earnings,
        'week_earnings':      week_earnings,
        'month_earnings':     month_earnings,
    })
