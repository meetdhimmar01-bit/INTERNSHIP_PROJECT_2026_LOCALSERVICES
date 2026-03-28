from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from datetime import datetime
import random
import time
from .models import User


# ── helpers ──────────────────────────────────────────────────────────────────

def _generate_otp():
    """Generate a 6-digit OTP."""
    return str(random.randint(100000, 999999))


def _send_otp_email(email, name, otp):
    """Send OTP verification email."""
    subject = '🔐 Your OTP Code – LocalServices Management'
    body = f"""Hi {name},

Thank you for registering on LocalServices Management!

To complete your account setup, please enter the following OTP:

  ┌─────────────────┐
  │   OTP: {otp}   │
  └─────────────────┘

This OTP is valid for 10 minutes only.

If you did not request this, please ignore this email.

— LocalServices Management Team
"""
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        return True
    except Exception:
        return False


def _send_welcome_email(user):
    """Send a welcome email when a new user registers."""
    subject = '🎉 Welcome to LocalServices Management!'
    body = f"""Hi {user.name},

Your account has been successfully created on LocalServices Management.

  📧 Email : {user.email}
  👤 Role  : {user.role.capitalize()}
  🕐 Joined: {datetime.now().strftime('%d %b %Y, %I:%M %p')}

You can now login at: http://127.0.0.1:8000/core/login/

Thank you for joining us!

— LocalServices Management Team
"""
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
    except Exception:
        pass   # Don't block signup if email fails


def _send_login_alert(user):
    """Send a login notification email."""
    subject = '🔔 New Login to Your LocalServices Account'
    body = f"""Hi {user.name},

A new login was detected on your LocalServices account.

  📧 Email  : {user.email}
  🕐 Time   : {datetime.now().strftime('%d %b %Y, %I:%M %p')}

If this was you, no action is needed.
If you did NOT login, please reset your password immediately.

— LocalServices Management Team
"""
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
    except Exception:
        pass   # Don't block login if email fails


def _notify_admins_of_pending_request(new_user):
    """Notify all existing approved admins about a new pending admin signup."""
    admins = User.objects.filter(role='admin', is_approved=True)
    admin_emails = list(admins.values_list('email', flat=True))
    if not admin_emails:
        return
    subject = '🔔 New Admin Approval Request – LocalServices'
    body = f"""Hello Admin,

A new user has registered and is requesting Admin access on LocalServices Management.

  👤 Name  : {new_user.name}
  📧 Email : {new_user.email}
  🕐 Time  : {datetime.now().strftime('%d %b %Y, %I:%M %p')}

Please login to your Admin Dashboard to approve or reject this request:
  http://127.0.0.1:8000/dashboards/admin/

— LocalServices Management (Automated Alert)
"""
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, admin_emails, fail_silently=False)
    except Exception:
        pass


# ── views ─────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)

    if request.method == 'POST':
        email    = request.POST.get('email')
        password = request.POST.get('password')
        user     = authenticate(request, username=email, password=password)
        if user is not None:
            # Block unapproved admin accounts
            if user.role == 'admin' and not user.is_approved:
                messages.error(request, 'Your admin account is pending approval. Please wait for the existing admin to approve your request.')
            else:
                login(request, user)
                _send_login_alert(user)
                return redirect_by_role(user)
        else:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'core/login.html')


def signup_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)

    if request.method == 'POST':
        first_name       = request.POST.get('first_name', '').strip()
        last_name        = request.POST.get('last_name', '').strip()
        name             = f"{first_name} {last_name}".strip() or 'User'
        email            = request.POST.get('email', '').strip()
        password         = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        role             = request.POST.get('role', 'user')
        # Security: prevent admin self-assignment via public signup
        if role not in ('user', 'owner'):
            role = 'user'

        # ── Validations ──
        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'core/signup.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'An account with this email already exists.')
            return render(request, 'core/signup.html')

        # ── Generate & store OTP in session ──
        otp = _generate_otp()
        request.session['otp_data'] = {
            'otp'       : otp,
            'otp_time'  : time.time(),          # Unix timestamp for expiry check
            'name'      : name,
            'email'     : email,
            'password'  : password,
            'role'      : role,
        }

        # ── Send OTP email ──
        sent = _send_otp_email(email, name, otp)
        if not sent:
            messages.error(request, 'Could not send OTP email. Please try again.')
            return render(request, 'core/signup.html')

        return redirect('core:verify_otp')

    return render(request, 'core/signup.html')


def verify_otp_view(request):
    """Verify the 6-digit OTP the user received via email."""
    otp_data = request.session.get('otp_data')

    # Guard: if no OTP session data, send back to signup
    if not otp_data:
        messages.error(request, 'Session expired. Please sign up again.')
        return redirect('core:signup')

    if request.method == 'POST':
        action = request.POST.get('action', 'verify')

        # ── Resend OTP ──
        if action == 'resend':
            new_otp = _generate_otp()
            otp_data['otp']      = new_otp
            otp_data['otp_time'] = time.time()
            request.session['otp_data'] = otp_data
            request.session.modified = True

            sent = _send_otp_email(otp_data['email'], otp_data['name'], new_otp)
            if sent:
                messages.success(request, f"New OTP sent to {otp_data['email']}.")
            else:
                messages.error(request, 'Could not resend OTP. Please try again.')
            return redirect('core:verify_otp')

        # ── Verify OTP ──
        entered_otp = (
            request.POST.get('d1', '') +
            request.POST.get('d2', '') +
            request.POST.get('d3', '') +
            request.POST.get('d4', '') +
            request.POST.get('d5', '') +
            request.POST.get('d6', '')
        ).strip()

        # Check expiry (10 minutes = 600 seconds)
        elapsed = time.time() - otp_data.get('otp_time', 0)
        if elapsed > 600:
            messages.error(request, 'OTP has expired. Please request a new one.')
            return render(request, 'core/password.html', {'step': 'verify_otp', 'email': otp_data['email']})

        if entered_otp != otp_data['otp']:
            messages.error(request, 'Incorrect OTP. Please try again.')
            return render(request, 'core/password.html', {'step': 'verify_otp', 'email': otp_data['email']})

        # ── Prevent IntegrityError if user refreshes after creation ──
        if User.objects.filter(email=otp_data['email']).exists():
            messages.success(request, 'Your account has already been verified. Please log in.')
            if 'otp_data' in request.session:
                del request.session['otp_data']
                request.session.modified = True
            return redirect('core:login')

        # ── OTP Correct — Create user ──
        is_approved = False if otp_data['role'] == 'admin' else True
        user = User.objects.create_user(
            email    = otp_data['email'],
            name     = otp_data['name'],
            password = otp_data['password'],
            role     = otp_data['role'],
            is_approved = is_approved,
        )

        # Clear OTP session data
        del request.session['otp_data']
        request.session.modified = True

        _send_welcome_email(user)

        if user.role == 'admin':
            _notify_admins_of_pending_request(user)
            messages.success(request, 'Your admin account has been created and is pending approval.')
            return redirect('core:login')

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect_by_role(user)

    return render(request, 'core/password.html', {'step': 'verify_otp', 'email': otp_data['email']})


def logout_view(request):
    logout(request)
    return redirect('core:login')


def redirect_by_role(user):
    if user.role == 'admin':
        return redirect('dashboards:admin')
    elif user.role == 'owner':
        return redirect('dashboards:owner')
    else:
        return redirect('dashboards:user')


# ── Forgot / Reset Password ────────────────────────────────────────────────────

def forgot_password_view(request):
    """Step 1: User enters their email to receive a reset OTP."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'No account found with that email address.')
            return render(request, 'core/password.html', {'step': 'forgot'})

        otp = _generate_otp()
        subject = '🔑 Password Reset OTP – LocalServices Management'
        body = f"""Hi {user.name},

We received a request to reset your password on LocalServices Management.

Your OTP code is:

  ┌─────────────────┐
  │   OTP: {otp}   │
  └─────────────────┘

This OTP is valid for 10 minutes. If you did not request a password reset, ignore this email.

— LocalServices Management Team
"""
        try:
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
            sent = True
        except Exception:
            sent = False

        request.session['reset_otp']       = otp
        request.session['reset_otp_email'] = email
        request.session['reset_otp_ts']    = time.time()

        if sent:
            messages.success(request, f'OTP sent to {email}. Check your inbox.')
        else:
            messages.warning(request, f'Could not send email (server not configured). OTP: {otp}')
        return redirect('core:reset_otp')

    return render(request, 'core/password.html', {'step': 'forgot'})


def reset_otp_view(request):
    """Step 2: Verify the OTP sent to email."""
    email = request.session.get('reset_otp_email')
    if not email:
        return redirect('core:forgot_password')

    if request.method == 'POST':
        entered = ''.join([
            request.POST.get(f'otp{i}', '') for i in range(1, 7)
        ])
        stored     = request.session.get('reset_otp')
        ts         = request.session.get('reset_otp_ts', 0)
        expired    = (time.time() - ts) > 600  # 10 min

        if expired:
            messages.error(request, 'OTP has expired. Please request a new one.')
            return redirect('core:forgot_password')

        if entered == stored:
            request.session['reset_verified'] = True
            return redirect('core:reset_password')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')

    return render(request, 'core/password.html', {'step': 'otp', 'email': email})


def reset_password_view(request):
    """Step 3: Set new password after OTP verification."""
    if not request.session.get('reset_verified'):
        return redirect('core:forgot_password')

    email = request.session.get('reset_otp_email')

    if request.method == 'POST':
        password         = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
        elif len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
        else:
            try:
                user = User.objects.get(email=email)
                user.set_password(password)
                user.save()
                # Clear reset session keys
                for key in ('reset_otp', 'reset_otp_email', 'reset_otp_ts', 'reset_verified'):
                    request.session.pop(key, None)
                messages.success(request, 'Password reset successfully! You can now log in.')
                return redirect('core:login')
            except User.DoesNotExist:
                messages.error(request, 'User not found.')

    return render(request, 'core/password.html', {'step': 'reset', 'email': email})
