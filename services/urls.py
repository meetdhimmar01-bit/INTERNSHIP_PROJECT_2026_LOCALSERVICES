from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('all/', views.services_list, name='list'),
    path('detail/<int:pk>/', views.service_detail, name='detail'),
]
