from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

class SubmissaoThrottle(UserRateThrottle):
    scope = 'submissoes'


class PublicoThrottle(AnonRateThrottle):
    """Leitura pública do acervo: limite alto por IP (visitantes de uma mesma rede/NAT institucional)."""
    scope = 'publico'
