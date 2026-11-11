"""Configuração de implantação: valores sensíveis obrigatórios pelo ambiente."""
import os
from django.core.exceptions import ImproperlyConfigured
from .settings import *

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
DEBUG = False
ALLOWED_HOSTS = os.environ['DJANGO_ALLOWED_HOSTS'].split(',')
ADMIN_NETWORKS = os.environ['ADMIN_NETWORKS'].split(',')
if not os.environ.get('REDIS_URL'):
    raise ImproperlyConfigured('REDIS_URL é obrigatório em produção.')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600
MAILERS = {'default': {'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
    'OPTIONS': {'host': os.environ['SMTP_HOST'], 'port': int(os.environ.get('SMTP_PORT', '587')),
    'use_tls': True, 'username': os.environ.get('SMTP_USER', ''), 'password': os.environ.get('SMTP_PASSWORD', '')}}}
DEFAULT_FROM_EMAIL = os.environ['DEFAULT_FROM_EMAIL']
