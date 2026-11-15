"""Suíte no PostgreSQL/Redis isolados. Não usar no servidor da aplicação."""
from .settings import *
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
# Redis real continua ativo; as filas são verificadas separadamente.
