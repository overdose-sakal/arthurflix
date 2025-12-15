# users/middleware.py

from django.contrib import auth, messages
from django.shortcuts import redirect
from django.conf import settings

class SingleSessionMiddleware:
    """
    Enforces that a user can only have one active session key. 
    If a user logs in elsewhere, their older session is invalidated and they are logged out.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                # Access the tracker via the related_name 'session_tracker'
                tracker = request.user.session_tracker
                
                # If the current session key does NOT match the stored active key
                if tracker.session_key != request.session.session_key:
                    
                    # 1. Log the user out
                    auth.logout(request)
                    
                    # 2. Add a message to display upon redirection
                    # 👇 UPDATED MESSAGE HERE 👇
                    messages.warning(
                        request, 
                        "Sorry, you can only login from one device at a time."
                    )
                    
                    # 3. Redirect to the login page (defined in settings.LOGIN_URL)
                    return redirect(settings.LOGIN_URL)
                    
            except AttributeError:
                # Handles users who logged in before this feature was enabled.
                pass 
            except Exception:
                # General exception handling
                pass

        response = self.get_response(request)
        return response