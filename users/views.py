# users/views.py (FIXED)

from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.db import models
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

# Import Forms and Models from the local app directory
from .forms import LoginForm, RegistrationForm, MembershipKeyForm 
from .models import MembershipKey 
from django.contrib.auth.models import User # Use this if you are using Django's default User model

# --- DECORATOR: membership_required ---
def membership_required(view_func):
    """
    Decorator to check if a logged-in user has a valid, active membership key.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            try:
                # Check if the user is linked to a valid MembershipKey
                key = MembershipKey.objects.get(user=request.user)
                if key.is_valid():
                    return view_func(request, *args, **kwargs)
                else:
                    # Key exists but is expired/inactive.
                    return redirect(reverse('activate_membership')) 
            except MembershipKey.DoesNotExist:
                # User is logged in but has no associated key.
                return redirect(reverse('activate_membership'))
        
        # If not authenticated, redirect to the standard login page.
        return redirect(reverse('login')) 
    
    return wrapper


# --- VIEW: user_login (Called by name='login') ---
def user_login(request):
    if request.user.is_authenticated:
        # Check for valid key, redirecting to home or key activation
        try:
            key = MembershipKey.objects.get(user=request.user)
            if key.is_valid():
                return redirect(reverse('home'))
        except MembershipKey.DoesNotExist:
            pass # Continue to key check below
            
        # User is logged in but has no valid key
        return redirect(reverse('activate_membership'))

    if request.method == 'POST':
        form = LoginForm(request.POST) 
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user) # This triggers the single-session signal
                
                # After login, redirect to key check page
                return redirect(reverse('activate_membership')) 
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()

    # CRITICAL FIX: Use 'users/login.html' here
    return render(request, 'users/login.html', {'form': form})


# --- VIEW: user_register (Called by name='register') ---
def user_register(request):
    if request.user.is_authenticated:
        return redirect(reverse('home'))

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.set_password(form.cleaned_data['password'])
            new_user.save()
            
            # Auto-log the user in immediately after successful registration
            user = authenticate(request, username=new_user.username, password=form.cleaned_data['password'])
            if user is not None:
                login(request, user)
                messages.success(request, 'Registration successful. Please activate your membership.')
                return redirect(reverse('activate_membership'))
            else:
                messages.success(request, 'Registration successful. You can now log in.')
                return redirect(reverse('login'))
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RegistrationForm()
    
    # CRITICAL FIX: Use 'users/register.html' here
    return render(request, 'users/register.html', {'form': form})


# --- VIEW: user_logout (Called by name='logout') ---
@login_required
def user_logout(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect(reverse('login'))


# --- VIEW: activate_membership (Called by name='activate_membership') ---
@login_required
def activate_membership(request):
    if not request.user.is_authenticated:
        messages.error(request, "Please log in first.")
        return redirect(reverse('login'))

    # Check if key is already valid
    try:
        key = MembershipKey.objects.get(user=request.user)
        if key.is_valid():
             messages.info(request, "Your membership is already active. Redirecting you to home.")
             return redirect(reverse('home'))
    except MembershipKey.DoesNotExist:
        key = None

    if request.method == 'POST':
        form = MembershipKeyForm(request.POST)
        if form.is_valid():
            entered_key = form.cleaned_data.get('key')
            
            try:
                # Find an active key that matches the entered key
                valid_key = MembershipKey.objects.get(key=entered_key, is_active=True)
                
                if valid_key.user is None:
                    # Key is free, assign it to the current user
                    valid_key.user = request.user
                    valid_key.save()
                    messages.success(request, "Membership key validated. Welcome!")
                    return redirect(reverse('home'))
                elif valid_key.user == request.user:
                    # Key is already owned by the user but wasn't passing is_valid() check
                    messages.warning(request, "Your key is active but might have been recently expired or was not linked.")
                    return redirect(reverse('home'))
                else:
                    # Key is owned by another user
                    messages.error(request, "This membership key is already in use by another account.")
            
            except MembershipKey.DoesNotExist:
                messages.error(request, "Invalid, inactive, or expired membership key.")
    else:
        form = MembershipKeyForm()
        
    # CRITICAL FIX: Use 'users/activate_membership.html' here
    return render(request, 'users/activate_membership.html', {'form': form})