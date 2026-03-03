from django.shortcuts import render
from .models import Category, Service

def home_view(request):
    categories = Category.objects.all()
    top_services = Service.objects.filter(is_active=True)[:6]
    return render(request, 'services/home.html', {
        'categories': categories,
        'top_services': top_services,
    })

from django.db.models import Q

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

