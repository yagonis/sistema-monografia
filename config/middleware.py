from ipaddress import ip_address, ip_network
from django.conf import settings
from django.http import HttpResponseForbidden


def rede_autorizada(request):
    try:
        origem = ip_address(request.META.get('REMOTE_ADDR', ''))
        return any(origem in ip_network(rede) for rede in settings.ADMIN_NETWORKS)
    except ValueError:
        return False


class RedeAdministrativaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        if request.path.startswith('/admin/'):
            if not rede_autorizada(request):
                return HttpResponseForbidden('Administração disponível somente na rede autorizada.')
        return self.get_response(request)


class AuditoriaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        from monografias.contexto import ator_atual
        token = ator_atual.set(request.user)
        try:
            return self.get_response(request)
        finally:
            ator_atual.reset(token)
