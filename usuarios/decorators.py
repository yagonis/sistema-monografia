from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def exige_perfil(perfil):
    def decorar(view):
        @login_required
        @wraps(view)
        def protegida(request, *args, **kwargs):
            if not getattr(request.user, perfil):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return protegida
    return decorar
