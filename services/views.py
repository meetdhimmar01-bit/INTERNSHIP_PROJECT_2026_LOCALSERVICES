from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from .models import Category, Service, Booking, Review, Wishlist

# ──────────────────────────────────────────────────────────────────────────────
# HOME & SERVICE LIST
# ──────────────────────────────────────────────────────────────────────────────

def home_view(request):
    categories = Category.objects.all()
    top_services = Service.objects.filter(is_active=True)[:6]
    return render(request, 'services/home.html', {
        'categories': categories,
        'top_services': top_services,
    })


def services_list(request):
    """Service listing with advanced search & filters."""
    services = Service.objects.filter(is_active=True).select_related('category', 'owner')
    categories = Category.objects.all()

    # ── Search ──
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    min_rating = request.GET.get('min_rating', '')
    sort_by = request.GET.get('sort_by', '')

    if query:
        services = services.filter(Q(name__icontains=query) | Q(category__name__icontains=query))

    if category_id:
        services = services.filter(category__id=category_id)

    if min_price:
        try:
            services = services.filter(base_price__gte=float(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            services = services.filter(base_price__lte=float(max_price))
        except ValueError:
            pass

    # Annotate with avg_rating for filtering/sorting
    services = services.annotate(avg_rating_val=Avg('bookings__review__rating'))

    if min_rating:
        try:
            services = services.filter(avg_rating_val__gte=float(min_rating))
        except ValueError:
            pass

    # ── Sort ──
    if sort_by == 'price_asc':
        services = services.order_by('base_price')
    elif sort_by == 'price_desc':
        services = services.order_by('-base_price')
    elif sort_by == 'rating_desc':
        services = services.order_by('-avg_rating_val')
    elif sort_by == 'newest':
        services = services.order_by('-id')
    else:
        services = services.order_by('-id')

    # Wishlist IDs for logged-in user
    wishlist_ids = []
    if request.user.is_authenticated:
        wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('service_id', flat=True))

    return render(request, 'services/servicelist.html', {
        'services': services,
        'categories': categories,
        'query': query,
        'category_id': category_id,
        'min_price': min_price,
        'max_price': max_price,
        'min_rating': min_rating,
        'sort_by': sort_by,
        'wishlist_ids': wishlist_ids,
    })


def service_detail(request, pk):
    service = get_object_or_404(Service, pk=pk, is_active=True)
    from .models import ProviderAvailability
    from django.utils import timezone
    import datetime

    reviews = Review.objects.filter(booking__service=service).select_related('booking__customer')
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']

    # Upcoming availability slots for this service owner
    today = timezone.now().date()
    availability_slots = []
    if service.owner:
        availability_slots = ProviderAvailability.objects.filter(
            provider=service.owner,
            date__gte=today,
            is_available=True,
        ).order_by('date', 'start_time')[:20]

    # Wishlist check
    is_wishlisted = False
    if request.user.is_authenticated:
        is_wishlisted = Wishlist.objects.filter(user=request.user, service=service).exists()

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to book a service.')
            return redirect('core:login')

        scheduled_date = request.POST.get('scheduled_date', '')
        scheduled_time = request.POST.get('scheduled_time', '')
        address = request.POST.get('address', '').strip()
        notes = request.POST.get('notes', '').strip()

        if not scheduled_date or not address:
            messages.error(request, 'Please fill in the scheduled date and address.')
        else:
            booking = Booking.objects.create(
                customer=request.user,
                provider=service.owner,
                service=service,
                scheduled_date=scheduled_date,
                scheduled_time=scheduled_time or None,
                address=address,
                notes=notes,
                status='Pending',
                payment_status='Unpaid',
            )
            # Notify provider
            if service.owner:
                _create_notification(
                    user=service.owner,
                    title='New Booking Request',
                    message=f'{request.user.name} has requested a booking for "{service.name}" on {scheduled_date}.',
                    notif_type='booking',
                    link=f'/dashboards/owner/',
                )
                # Email to provider
                _send_booking_email_to_provider(booking)

            messages.success(request, f'Your booking for "{service.name}" has been submitted! We will confirm it shortly.')
            return redirect('services:detail', pk=service.pk)

    return render(request, 'services/service_detail.html', {
        'service': service,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'availability_slots': availability_slots,
        'is_wishlisted': is_wishlisted,
    })


# ──────────────────────────────────────────────────────────────────────────────
# MAP VIEW
# ──────────────────────────────────────────────────────────────────────────────

def map_view(request):
    """Map view with all services that have location data."""
    services_qs = Service.objects.filter(is_active=True).select_related('category', 'owner')
    services_data = []
    for s in services_qs:
        lat = float(s.latitude) if s.latitude else None
        lng = float(s.longitude) if s.longitude else None
        services_data.append({
            'id': s.id,
            'name': s.name,
            'category': s.category.name if s.category else '',
            'price': str(s.base_price),
            'lat': lat,
            'lng': lng,
            'url': f'/services/detail/{s.id}/',
            'image': s.image.url if s.image else '',
        })
    return render(request, 'services/map.html', {
        'services_json': services_data,
        'all_services': services_qs,
    })


# ──────────────────────────────────────────────────────────────────────────────
# PAYMENT (RAZORPAY)
# ──────────────────────────────────────────────────────────────────────────────

@login_required
def initiate_payment(request, booking_id):
    """Create a Razorpay order and show the payment page."""
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)

    if booking.payment_status == 'Paid':
        messages.info(request, 'This booking is already paid.')
        return redirect('dashboards:user')

    try:
        import razorpay
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        amount_paise = int(booking.service.base_price * 100)  # Razorpay uses paise
        order = client.order.create({
            'amount': amount_paise,
            'currency': 'INR',
            'receipt': f'booking_{booking.id}',
            'notes': {'booking_id': booking.id},
        })
        booking.payment_order_id = order['id']
        booking.save()
        return render(request, 'services/payment.html', {
            'booking': booking,
            'razorpay_key': settings.RAZORPAY_KEY_ID,
            'order': order,
            'amount_paise': amount_paise,
        })
    except Exception as e:
        messages.error(request, f'Payment initiation failed: {e}')
        return redirect('dashboards:user')


@require_POST
@login_required
def verify_payment(request):
    """Verify Razorpay payment signature and mark booking as Paid."""
    import razorpay
    import hmac
    import hashlib

    payment_id = request.POST.get('razorpay_payment_id', '')
    order_id = request.POST.get('razorpay_order_id', '')
    signature = request.POST.get('razorpay_signature', '')

    # Find booking by order_id
    booking = get_object_or_404(Booking, payment_order_id=order_id, customer=request.user)

    # Verify signature
    key_secret = settings.RAZORPAY_KEY_SECRET.encode('utf-8')
    message = f'{order_id}|{payment_id}'.encode('utf-8')
    expected_sig = hmac.new(key_secret, message, hashlib.sha256).hexdigest()

    if expected_sig == signature:
        booking.payment_id = payment_id
        booking.payment_status = 'Paid'
        booking.save()
        # Notify customer
        _create_notification(
            user=request.user,
            title='Payment Successful',
            message=f'Payment for booking #{booking.id} ({booking.service.name}) was successful.',
            notif_type='payment',
            link='/dashboards/user/',
        )
        # Notify provider
        if booking.provider:
            _create_notification(
                user=booking.provider,
                title='Payment Received',
                message=f'Payment received for booking #{booking.id} from {request.user.name}.',
                notif_type='payment',
                link='/dashboards/owner/',
            )
        return render(request, 'services/payment_status.html', {
            'success': True,
            'booking': booking,
        })
    else:
        return render(request, 'services/payment_status.html', {
            'success': False,
            'booking': booking,
        })


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _create_notification(user, title, message, notif_type='system', link=''):
    from .models import Notification
    try:
        Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notif_type=notif_type,
            link=link,
        )
    except Exception:
        pass


def _send_booking_email_to_provider(booking):
    from django.core.mail import send_mail
    if not booking.provider:
        return
    try:
        send_mail(
            f'📋 New Booking Request – {booking.service.name}',
            f"""Hi {booking.provider.name},

You have a new booking request on LocalServices!

  📌 Service  : {booking.service.name}
  👤 Customer : {booking.customer.name}
  📅 Date     : {booking.scheduled_date}
  🕐 Time     : {booking.scheduled_time or 'Not specified'}
  📍 Address  : {booking.address}

Please login to your dashboard to Approve or Reject this booking:
http://127.0.0.1:8000/dashboards/owner/

— LocalServices Team
""",
            settings.DEFAULT_FROM_EMAIL,
            [booking.provider.email],
            fail_silently=True,
        )
    except Exception:
        pass
