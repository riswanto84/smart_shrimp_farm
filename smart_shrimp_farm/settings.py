from pathlib import Path
import os
try:
    from decouple import config
except Exception:
    def config(name, default=None, cast=None):
        value = os.environ.get(name, default)
        if cast is bool:
            return str(value).lower() in {'1', 'true', 'yes', 'on'}
        return value
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('SECRET_KEY','django-insecure-smart-shrimp-farm-dev')
DEBUG = os.environ.get('DEBUG','True') == 'True'
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    ".ngrok-free.app",
    ".ngrok.io",
]

CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://*.ngrok-free.app",
    "https://*.ngrok.io",
]
INSTALLED_APPS = [
 'django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles',
 'accounts','core','ponds','operations','sales','finance','investor','weather_ai','chat_ai'
]
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'smart_shrimp_farm.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.debug','django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages','accounts.context_processors.user_roles','core.context_processors.app_notifications'],'builtins':['core.templatetags.currency']}}]
WSGI_APPLICATION = 'smart_shrimp_farm.wsgi.application'
DATABASES = {'default': {'ENGINE':'django.db.backends.sqlite3','NAME': BASE_DIR/'db.sqlite3'}}
LANGUAGE_CODE='id-id'; TIME_ZONE='Asia/Jakarta'; USE_I18N=True; USE_TZ=True
STATIC_URL='static/'; 

STATIC_ROOT = BASE_DIR / "staticfiles"



STATICFILES_DIRS=[BASE_DIR/'static']
MEDIA_URL='/media/'; 
MEDIA_ROOT=BASE_DIR/'media'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
LOGIN_URL='/accounts/login/'; LOGIN_REDIRECT_URL='/dashboard/'; LOGOUT_REDIRECT_URL='/'
EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'
# Ollama lokal untuk Chat AI Tambak
OLLAMA_URL = config('OLLAMA_URL', default='http://localhost:11434')
OLLAMA_MODEL = config('OLLAMA_MODEL', default='gemma2:2b')
FARM_LAT=float(os.environ.get('FARM_LAT','-5.98'))
FARM_LON=float(os.environ.get('FARM_LON','107.02'))

# Midtrans payment gateway
# Gunakan Sandbox dulu. Isi key lewat environment/.env, jangan commit secret production ke Git.
MIDTRANS_IS_PRODUCTION = config('MIDTRANS_IS_PRODUCTION', default=False, cast=bool)
MIDTRANS_SERVER_KEY = config('MIDTRANS_SERVER_KEY', default='')
MIDTRANS_CLIENT_KEY = config('MIDTRANS_CLIENT_KEY', default='')
MIDTRANS_MERCHANT_ID = config('MIDTRANS_MERCHANT_ID', default='')
# APP_BASE_URL diperlukan agar callback dan webhook memakai domain publik, contoh: https://namadomain.com
APP_BASE_URL = config('APP_BASE_URL', default='')
