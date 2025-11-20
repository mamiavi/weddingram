import datetime

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone


class CountdownMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.wedding_date = datetime.datetime.strptime(f"{settings.WEDDING_DATE}", "%d-%m-%Y")

    def __call__(self, request):
        # Allow access to countdown page itself (avoid redirect loop)
        if request.path == reverse("countdown"):
            return self.get_response(request)

        # Allow access to admin
        if request.path.startswith('/admin/'):
            return self.get_response(request)

        # Redirect if before start time
        now = timezone.now()
        if now < self.wedding_date:
            return redirect("countdown")

        return self.get_response(request)
