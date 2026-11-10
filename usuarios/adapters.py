from allauth.account.adapter import DefaultAccountAdapter


class AdaptadorConta(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        # Contas e papéis são atribuídos pela administração institucional.
        return False
