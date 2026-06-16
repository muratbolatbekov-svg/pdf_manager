from functools import wraps

from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _

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
                raise PermissionDenied(_('Недостаточно прав для этого действия.'))
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def can_manage_documents(user):
    return get_user_role(user) in (UserProfile.ROLE_MANAGER, UserProfile.ROLE_ADMIN)


def can_manage_users(user):
    return get_user_role(user) == UserProfile.ROLE_ADMIN
