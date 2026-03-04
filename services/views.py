from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q, Avg
from .models import Category, Service, Booking, Review

def home_view(request):
    categories = Category.objects.all()
    top_services = Service.objects.filter(is_active=True)[:6]
    return render(request, 'services/home.html', {
        'categories': categories,
        'top_services': top_services,
    })

def services_list(request):
    services = Service.objects.filter(is_active=True)
    categories = Category.objects.all()
    query = request.GET.get('q', '')

    if query:
        services = services.filter(Q(name__icontains=query) | Q(category__name__icontains=query))

    return render(request, 'services/servicelist.html', {
        'services': services,
        'categories': categories,
        'query': query
    })

def service_detail(request, pk):
    service = get_object_or_404(Service, pk=pk, is_active=True)

    # Reviews: all reviews for bookings of this service
    reviews = Review.objects.filter(booking__service=service).select_related('booking__customer')
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']

    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to book a service.')
            return redirect('core:login')

        scheduled_date = request.POST.get('scheduled_date', '')
        address = request.POST.get('address', '').strip()
        notes = request.POST.get('notes', '').strip()

        if not scheduled_date or not address:
            messages.error(request, 'Please fill in the scheduled date and address.')
        else:
            Booking.objects.create(
                customer=request.user,
                service=service,
                scheduled_date=scheduled_date,
                address=address,
                notes=notes,
                status='Pending',
                payment_status='Unpaid',
            )
            messages.success(request, f'Your booking for "{service.name}" has been submitted! We will confirm it shortly.')
            return redirect('services:detail', pk=service.pk)

    return render(request, 'services/service_detail.html', {
        'service': service,
        'reviews': reviews,
        'avg_rating': avg_rating,
    })
