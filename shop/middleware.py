# middleware.py
from django.shortcuts import redirect
from django.urls import reverse

class EmailVerifiedMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if not request.user.is_verified:
                allowed_paths = [
                    reverse('shop:verify_email'),  # Add exact url or use startswith
                    reverse('shop:logout'),
                    reverse('shop:email_verification_sent'),
                    '/admin/',  # Allow admin if needed
                ]
                if not any(request.path.startswith(path) for path in allowed_paths):
                    return redirect('shop:email_verification_sent')
        response = self.get_response(request)
        return response
