from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.models import User


@login_required
def owner_dashboard(request):
    return render(request, 'dashboards/owner.html')


@login_required
def user_dashboard(request):
    return render(request, 'dashboards/user.html')


@login_required
def admin_dashboard(request):
    from services.models import Service, Booking
    pending_admins = User.objects.filter(role='admin', is_approved=False).order_by('-date_joined')
    context = {
        'total_users':    User.objects.filter(role='user').count(),
        'total_owners':   User.objects.filter(role='owner').count(),
        'total_services': Service.objects.count(),
        'total_bookings': Booking.objects.count(),
        'pending_admins': pending_admins,
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
