"""Consultas de autorização reutilizáveis pelos fluxos HTML e futura API."""
from .models import Monografia


def monografias_da_coordenacao(usuario):
    if not usuario.is_authenticated or not usuario.eh_coordenador:
        return Monografia.objects.none()
    return Monografia.objects.filter(curso__coordenador=usuario).exclude(
        status=Monografia.Status.RASCUNHO,
    )
