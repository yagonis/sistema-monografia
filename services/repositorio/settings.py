import os
SECRET_KEY = os.environ.get('REPOSITORIO_SECRET_KEY', 'local-repositorio-only')
DEBUG = False
ALLOWED_HOSTS = os.environ.get('REPOSITORIO_HOSTS', 'localhost,127.0.0.1,repositorio,testserver').split(',')
INSTALLED_APPS = ['services.repositorio.apps.RepositorioConfig']
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
ROOT_URLCONF = 'services.repositorio.urls'
DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql',
    'NAME': os.environ.get('REPOSITORIO_DB', 'repositorio_busca'),
    'USER': os.environ.get('REPOSITORIO_USER', 'busca'), 'PASSWORD': os.environ.get('REPOSITORIO_PASSWORD', ''),
    'HOST': os.environ.get('REPOSITORIO_DB_HOST', 'busca-db'), 'PORT': '5432'}}
if os.environ.get('REPOSITORIO_TEST_SQLITE') == '1':
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
REDIS_URL = os.environ.get('REPOSITORIO_REDIS_URL')
if REDIS_URL:
    CACHES = {'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache', 'LOCATION': REDIS_URL}}
INTEGRATION_KEY = os.environ.get('REPOSITORIO_INTEGRATION_KEY', '')
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware']
USE_TZ = True
DATA_UPLOAD_MAX_MEMORY_SIZE = 64 * 1024 * 1024
