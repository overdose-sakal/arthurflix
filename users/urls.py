# users/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Standard Django Authentication
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'), 
    path('logout/', views.user_logout, name='logout'),
    
    # Key Management
    path('key/activate/', views.activate_membership, name='activate_membership'),
    path("session-ended/", views.session_ended, name="session_ended"),

    # Profile
    path('profile/', views.user_profile, name='profile'),

    # Catalogue Management
    path('catalogue/toggle/', views.toggle_catalogue_item, name='toggle_catalogue'),
    path('catalogue/status/<int:movie_id>/', views.get_catalogue_status, name='get_catalogue_status'),

    path("profile/change-avatar/", views.change_avatar, name="change_avatar"),

]