from django.contrib import admin
from .models import Category, Service, ProviderProfile, Booking, Review


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ('name', 'description')
    search_fields = ('name',)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display  = ('name', 'category', 'base_price', 'is_active')
    list_filter   = ('category', 'is_active')
    search_fields = ('name',)
    list_editable = ('is_active',)


@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'experience_years', 'availability_status', 'contact_number')
    list_filter   = ('availability_status',)
    search_fields = ('user__email', 'user__name')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display  = ('id', 'service', 'customer', 'provider', 'status', 'payment_status', 'booking_date')
    list_filter   = ('status', 'payment_status')
    search_fields = ('customer__email', 'provider__email', 'service__name')
    readonly_fields = ('booking_date',)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display  = ('booking', 'rating', 'comment')
    list_filter   = ('rating',)

