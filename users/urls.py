# users/urls.py (FIXED)

from django.urls import path
from . import views

urlpatterns = [
    # Standard Django Authentication
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'), 
    path('logout/', views.user_logout, name='logout'),
    
    # Key Management (Activation page is required after login for new/expired users)
    path('key/activate/', views.activate_membership, name='activate_membership'),
]