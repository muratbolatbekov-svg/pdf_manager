from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .models import UserProfile


def get_user_role(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return UserProfile.ROLE_ADMIN
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile.role


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            role = get_user_role(request.user)
            if role not in roles:
                messages.error(request, 'Недостаточно прав для этого действия.')
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
