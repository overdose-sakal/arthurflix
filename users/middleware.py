# users/middleware.py

from django.contrib import auth, messages # <-- CRITICAL FIX: Ensure messages is imported
from django.http import HttpResponseRedirect
from django.urls import reverse
from urllib.parse import urlencode


class SingleSessionMiddleware:
    """
    Enforces single active session per user.
    If a different session_key is detected, logs out the user
    and redirects to /session-ended/?reason=duplicate_session
    """

    def __init__(self, get_response):
        self.get_response = get_response
        print("✅ SingleSessionMiddleware INITIALIZED")

    def __call__(self, request):
        print("🚨 SingleSessionMiddleware CALLED:", request.path)

        # Allow login page and session-ended page to load normally
        if request.path == reverse("login") or request.path == reverse("session_ended"):
            return self.get_response(request)

        if request.user.is_authenticated:
            print("👤 Authenticated user:", request.user)

            try:
                tracker = request.user.session_tracker

                current_key = request.session.session_key
                stored_key = tracker.session_key
                print("🧪 CHECKING DUPLICATE SESSION")
                print("🔑 STORED SESSION KEY :", stored_key)
                print("🔑 CURRENT SESSION KEY:", current_key)

                if not current_key or not stored_key:
                    print("⚠️ Missing session key, skipping check")
                    return self.get_response(request)

                # 🔥 DUPLICATE SESSION DETECTED
                if stored_key != current_key:
                    print("❌ DUPLICATE SESSION DETECTED")

                    messages.error(
                        request,
                        "Duplicate session detected. You have been forcibly logged out."
                    )
                    
                    auth.logout(request)
                    request.session.flush()

                    query = urlencode({"reason": "duplicate_session"})
                    
                    # FINAL REDIRECT: To the session_ended view
                    redirect_url = f"{reverse('session_ended')}?{query}"

                    print("➡️ Redirecting to:", redirect_url)

                    return HttpResponseRedirect(redirect_url)

            except Exception as e:
                # If an error occurs here, the redirect is bypassed.
                print("!!! CRITICAL FAILURE IN DUPLICATE SESSION CHECK !!!")
                print(f"⚠️ Session tracker error: {repr(e)}") # <--- REPORT THIS IF IT FAILS AGAIN

        return self.get_response(request)