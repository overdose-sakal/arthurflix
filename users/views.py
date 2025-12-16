# users/views.py
from functools import wraps
from collections import defaultdict
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from functools import wraps
from django.conf import settings
from django.contrib.auth.decorators import user_passes_test

def login_not_required(function=None):
    """
    Decorator for views that checks that the user is *not* logged in,
    redirecting to the URL specified in settings.LOGIN_REDIRECT_URL if 
    they are.
    
    This is useful for views like registration, login, and password reset
    pages, which shouldn't be accessible to authenticated users.
    
    Requires the request context to be used in the template rendering
    if the view needs access to the user object (e.g., to check if 
    they are authenticated, even though this decorator redirects if they are).
    
    The default redirect URL is 'settings.LOGIN_REDIRECT_URL'.
    """

    def check_not_logged_in(user):
        # Returns True if the user is NOT authenticated (i.e., not logged in).
        return not user.is_authenticated

    # The user_passes_test decorator handles the logic:
    # - If check_not_logged_in(request.user) is True, the original function runs.
    # - If check_not_logged_in(request.user) is False (user is authenticated), 
    #   it redirects to the failure URL (LOGIN_REDIRECT_URL).
    actual_decorator = user_passes_test(
        check_not_logged_in, 
        login_url=settings.LOGIN_REDIRECT_URL 
    )

    if function:
        # If the decorator is used as @login_not_required
        return actual_decorator(function)
    
    # If the decorator is used as @login_not_required()
    return actual_decorator


from .forms import LoginForm, RegistrationForm, MembershipKeyForm
from .models import (
    MembershipKey,
    UserSessionTracker,
    Avatar,
    UserProfile,
    UserCatalogueItem,
    MovieVisit,
)

from movies.models import Movies


# ---------------------------------
# DECORATOR: membership_required
# ---------------------------------
def membership_required(view_func):
    """
    Decorator to check if the user is logged in AND has a currently valid membership key.
    If not valid, redirects to the key activation page.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(reverse('login') + f"?next={request.path}")

        try:
            key = MembershipKey.objects.get(user=request.user, is_active=True)
            
            if key.is_valid: 
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "Your membership has expired. Please renew your key to continue.")
                return redirect(reverse('activate_membership'))
                
        except MembershipKey.DoesNotExist:
            messages.warning(request, "Please activate your membership key.")
            return redirect(reverse('activate_membership'))

    return wrapper


# ---------------------------------
# VIEW: user_login
# ---------------------------------
@login_not_required
def user_login(request):
    """Handles user login, authentication, and single-session enforcement."""
    if request.user.is_authenticated and not request.GET.get("reason"):
        return redirect(reverse('home'))

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {user.username}!")
                
                next_url = request.POST.get('next', reverse('home'))
                return redirect(next_url)
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = LoginForm()
        
    context = {
        'form': form,
        'reason': request.GET.get('reason', None)
    }
    return render(request, 'users/login.html', context)


# ---------------------------------
# VIEW: user_register
# ---------------------------------
@login_not_required
def user_register(request):
    avatars = Avatar.objects.all()
    
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        
        if form.is_valid():
            new_user = form.save()
            
            user = authenticate(
                username=new_user.username,
                password=form.cleaned_data["password"]
            )
            if user:
                login(request, user)

                tracker, _ = UserSessionTracker.objects.get_or_create(user=user)
                if not request.session.session_key:
                    request.session.save()
                tracker.session_key = request.session.session_key
                tracker.save()
            
            messages.success(request, "Registration successful. Please activate your membership.")
            return redirect("activate_membership")
    else:
        form = RegistrationForm()
        
    return render(request, "users/register.html", {
        "form": form,
        "avatars": avatars,
    })


# ---------------------------------
# VIEW: user_logout
# ---------------------------------
@login_required
def user_logout(request):
    """Handle user logout and clear the user's session tracker."""
    try:
        tracker = UserSessionTracker.objects.get(user=request.user)
        tracker.session_key = None
        tracker.save()
    except UserSessionTracker.DoesNotExist:
        pass 
        
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect(reverse('login'))


# ---------------------------------
# VIEW: activate_membership
# ---------------------------------
@login_required
def activate_membership(request):
    """
    Handles membership key activation and renewal.
    """
    renewal_message = None
    is_renewal = False
    current_key = None

    try:
        current_key = MembershipKey.objects.get(user=request.user)
        is_renewal = True

        expiry_date_str = current_key.expiry_date.strftime("%B %d, %Y") if current_key.expiry_date else "N/A"

        if current_key.is_valid:
            if not request.GET.get('force_renewal'):
                messages.info(request, "Your membership is already active.")
                return redirect(reverse('home'))
        
        renewal_message = (
            f"Your current membership expired on {expiry_date_str}. "
            "Please enter a new key to renew your subscription."
        )

    except MembershipKey.DoesNotExist:
        renewal_message = (
            f"Welcome, {request.user.username}. Please enter your 32-character membership key "
            "to activate your subscription."
        )

    if request.method == "POST":
        form = MembershipKeyForm(request.POST)
        if form.is_valid():
            key_value = form.cleaned_data['key']

            try:
                new_key = MembershipKey.objects.get(
                    key=key_value, 
                    user__isnull=True, 
                    is_active=True
                )
                
                if current_key:
                    current_key.user = None
                    current_key.is_active = False
                    current_key.save()
                
                new_key.user = request.user
                new_key.expiry_date = timezone.now().date() + timedelta(days=365)
                new_key.save()
                
                messages.success(request, f"Membership successfully activated! Expires on {new_key.expiry_date.strftime('%B %d, %Y')}.")
                return redirect(reverse('home'))
                
            except MembershipKey.DoesNotExist:
                messages.error(request, "Key is invalid, expired, or already assigned to another user.")
            except Exception as e:
                print(f"CRITICAL KEY PROCESSING ERROR: {e}") 
                messages.error(request, "An unexpected error occurred during key processing.")
        else:
            messages.error(request, "Please ensure the key is exactly 32 characters long.")
            
    else:
        form = MembershipKeyForm()
    
    context = {
        'form': form,
        'renewal_message': renewal_message,
        'is_renewal': is_renewal,
    }
    return render(request, 'users/activate_membership.html', context)


# ---------------------------------
# VIEW: user_profile
# ---------------------------------
@login_required
@membership_required
def user_profile(request):
    profile = get_object_or_404(UserProfile, user=request.user)

    # Catalogue items
    items = (
        UserCatalogueItem.objects
        .filter(user=request.user)
        .select_related("movie")
    )

    grouped = defaultdict(list)
    for item in items:
        grouped[item.status].append(item)

    # Recent visits (LAST 3)
    recent_visits = (
        MovieVisit.objects
        .filter(user=request.user)
        .select_related("movie")
        .order_by("-visited_at")[:3]
    )

    context = {
        "user": request.user,
        "profile": profile,
        "watchlist": grouped.get("watchlist", []),
        "finished": grouped.get("finished", []),
        "recent_visits": recent_visits,
    }

    from .models import Avatar

    avatars = Avatar.objects.all()

    context = {
        "user": request.user,
        "profile": profile,
        "watchlist": grouped.get("watchlist", []),
        "finished": grouped.get("finished", []),
        "recent_visits": recent_visits,
        "avatars": avatars,  # 👈 ADD THIS
    }


    return render(request, "users/profile.html", context)



# ---------------------------------
# VIEW: session_ended
# ---------------------------------
@login_not_required
def session_ended(request):
    """
    Renders the dedicated 'forced_logout.html' page when another device logs in.
    """
    return render(request, "users/forced_logout.html")


# ---------------------------------
# VIEW: toggle_catalogue_item
# ---------------------------------
@login_required
@membership_required
def toggle_catalogue_item(request):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=405)

    movie_id = request.POST.get("movie_id")
    status = request.POST.get("status")

    if not movie_id or status not in ["watchlist", "finished"]:
        return JsonResponse({"success": False, "message": "Invalid data"}, status=400)

    movie = get_object_or_404(Movies, id=movie_id)

    item, created = UserCatalogueItem.objects.get_or_create(
        user=request.user,
        movie=movie,
        defaults={"status": status},
    )

    if not created:
        if item.status == status:
            item.delete()
            return JsonResponse({
                "success": True,
                "action": "removed",
                "status": status
            })
        else:
            item.status = status
            item.save()

    return JsonResponse({
        "success": True,
        "action": "added",
        "status": status
    })

@login_required
@membership_required
def get_catalogue_status(request, movie_id):
    try:
        item = UserCatalogueItem.objects.get(
            user=request.user,
            movie_id=movie_id
        )
        return JsonResponse({
            "exists": True,
            "status": item.status
        })
    except UserCatalogueItem.DoesNotExist:
        return JsonResponse({
            "exists": False,
            "status": None
        })


@login_required
@membership_required
def change_avatar(request):
    if request.method != "POST":
        return redirect("profile")

    avatar_id = request.POST.get("avatar_id")
    if not avatar_id:
        messages.error(request, "No avatar selected.")
        return redirect("profile")

    avatar = get_object_or_404(Avatar, id=avatar_id)

    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile.avatar = avatar
    profile.save()

    messages.success(request, "Avatar updated successfully!")
    return redirect("profile")
