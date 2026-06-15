from .permissions import get_user_role


def user_role(request):
    return {'user_role': get_user_role(request.user) if request.user.is_authenticated else None}
