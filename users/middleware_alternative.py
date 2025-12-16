from django.contrib import auth
from django.http import HttpResponseRedirect
from django.conf import settings


class SingleSessionMiddleware:
    """
    Alternative implementation using settings.LOGIN_URL
    and direct URL construction to avoid any Django URL resolver issues.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                tracker = request.user.session_tracker
                
                # Check if current session matches the stored active session
                if tracker.session_key != request.session.session_key:
                    # User has logged in elsewhere - invalidate this session
                    
                    # 1. Log the user out (clears session completely)
                    auth.logout(request)
                    
                    # 2. Build redirect URL using LOGIN_URL from settings
                    # This approach avoids reverse() entirely
                    login_url = getattr(settings, 'LOGIN_URL', '/login/')
                    
                    # Ensure login_url doesn't already have query params
                    if '?' in login_url:
                        redirect_url = f"{login_url}&reason=duplicate_session"
                    else:
                        redirect_url = f"{login_url}?reason=duplicate_session"
                    
                    # 3. Return immediate redirect with explicit URL
                    return HttpResponseRedirect(redirect_url)
                    
            except AttributeError:
                # User doesn't have a session_tracker
                pass
            except Exception:
                # Log in production, but don't crash
                pass

        response = self.get_response(request)
        return response


# ALTERNATIVE VERSION 2: Using request.build_absolute_uri()
class SingleSessionMiddlewareAbsolute:
    """
    Version that builds absolute URIs to ensure proper redirection.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                tracker = request.user.session_tracker
                
                if tracker.session_key != request.session.session_key:
                    auth.logout(request)
                    
                    # Build absolute URL
                    redirect_url = request.build_absolute_uri('/login/?reason=duplicate_session')
                    
                    return HttpResponseRedirect(redirect_url)
                    
            except AttributeError:
                pass
            except Exception:
                pass

        response = self.get_response(request)
        return response