from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('login/',           views.login_view,           name='login'),
    path('signup/',          views.signup_view,          name='signup'),
    path('logout/',          views.logout_view,          name='logout'),
    path('verify-otp/',      views.verify_otp_view,      name='verify_otp'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('reset-otp/',       views.reset_otp_view,       name='reset_otp'),
    path('reset-password/',  views.reset_password_view,  name='reset_password'),
]
