from rest_framework.throttling import UserRateThrottle

class SubmissaoThrottle(UserRateThrottle):
    scope = 'submissoes'
