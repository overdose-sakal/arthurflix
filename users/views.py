# users/views.py - COMPLETE with Login, Logout, Register, and Membership Activation

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from functools import wraps

# Imports for standard Django authentication and forms
from django.contrib.auth import authenticate, login, logout 
from django.contrib.auth.forms import UserCreationForm # NEW Import

from .models import MembershipKey 


# --- Decorator for Two-Step Access Control ---

def membership_required(view_func):
    """
    DECORATOR: 
    1. Checks if the user is authenticated (username/password).
    2. Checks if the authenticated user has a valid, unexpired MembershipKey.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 1. Check Standard Authentication
        if not request.user.is_authenticated:
            # If not logged in, redirect to login page
            messages.info(request, "Please log in with your username and password.")
            return redirect(reverse('login') + f"?next={request.path}")
        
        # 2. Check Membership Status
        try:
            # Find an ACTIVE and unexpired key linked to the logged-in user
            valid_key = MembershipKey.objects.filter(
                user=request.user, 
                is_active=True,
                expiry_date__gt=timezone.now() # Check if not expired
            ).first()
            
            if not valid_key:
                # User is logged in, but has no valid membership key
                messages.warning(request, 
                               'Authentication successful, but you need a valid membership key to view content.')
                
                # Redirect to a page where they can enter/link their key
                return redirect(reverse('activate_membership'))

            # Success: User is authenticated AND has a valid key
            request.membership_key = valid_key # Attach key object for use in views
            return view_func(request, *args, **kwargs)

        except Exception as e:
            # Internal error during key check
            print(f"Membership check error: {e}")
            messages.error(request, 'An internal error occurred with membership verification.')
            return redirect(reverse('login'))

    return wrapper

# --- Standard Django Authentication Views ---

def user_login(request):
    """ Handles standard Django username/password login. """
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            next_url = request.POST.get('next') or reverse('home')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid Username or Password.')
        
    return render(request, 'users/login.html', {})

# --- NEW REGISTRATION VIEW ---
def user_register(request):
    """ Handles new user registration. """
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the user in immediately after registration
            login(request, user)
            messages.success(request, 'Account created successfully! Please activate your membership key now.')
            # Redirect to the key activation page
            return redirect(reverse('activate_membership')) 
        else:
            # Form is invalid (e.g., passwords didn't match, username taken)
            for field, errors in form.errors.items():
                for error in errors:
                    # Display the first error to the user
                    messages.error(request, f"{error}")
                    break
            
    else:
        form = UserCreationForm()
        
    return render(request, 'users/register.html', {'form': form})
# -----------------------------

def user_logout(request):
    """ Logs the user out and clears the session. """
    logout(request)
    messages.info(request, "You have been successfully logged out.")
    return redirect(reverse('login'))


# --- Membership Key Association View ---

def activate_membership(request):
    """ Allows a logged-in user to associate a key with their account. """
    # If the user is not logged in, redirect them to the login page first
    if not request.user.is_authenticated:
        messages.info(request, "Please log in first before activating a key.")
        return redirect(reverse('login') + f"?next={reverse('activate_membership')}")

    # Check if they already have a valid key (to prevent unnecessary form submission)
    if MembershipKey.objects.filter(user=request.user, is_active=True, expiry_date__gt=timezone.now()).exists():
        messages.info(request, "You already have an active membership. Redirecting to home.")
        return redirect('home')
    
    if request.method == 'POST':
        submitted_key = request.POST.get('key', '').strip()
        
        try:
            key_instance = MembershipKey.objects.get(key=submitted_key, is_active=True)
            
            if not key_instance.is_valid():
                messages.error(request, 'This key is expired or inactive.')
            elif key_instance.user is not None and key_instance.user != request.user:
                messages.error(request, 'This key is already in use by another account.')
            else:
                # Success: Associate the key with the currently logged-in user
                key_instance.user = request.user
                key_instance.save()
                messages.success(request, 'Membership key successfully linked! Full access granted.')
                return redirect('home') 
                
        except MembershipKey.DoesNotExist:
            messages.error(request, 'Invalid or non-existent membership key.')
        
    return render(request, 'users/activate_membership.html', {})