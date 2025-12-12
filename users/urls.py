# users/urls.py - Updated with Registration

from django.urls import path
from . import views

urlpatterns = [
    # Standard Django Authentication
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'), # NEW REGISTRATION PATH
    path('logout/', views.user_logout, name='logout'),
    

    # Key Management (Link key to logged-in user)
    path('key/activate/', views.activate_membership, name='activate_membership'),
]