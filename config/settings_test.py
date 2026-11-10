"""Testes isolados: não acessam o PostgreSQL nem arquivos reais de upload."""
import os

os.environ.setdefault('DB_PASSWORD', 'test-only')
from .settings import *  # noqa: F403,E402

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
