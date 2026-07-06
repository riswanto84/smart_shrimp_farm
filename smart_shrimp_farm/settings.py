from pathlib import Path
import os
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('SECRET_KEY','django-insecure-smart-shrimp-farm-dev')
DEBUG = os.environ.get('DEBUG','True') == 'True'
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok-free.app',
    'https://*.ngrok.io',
]
INSTALLED_APPS = [
 'django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles',
 'accounts','core','ponds','operations','sales','finance','investor','weather_ai','chat_ai'
]
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'smart_shrimp_farm.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.debug','django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages','accounts.context_processors.user_roles','core.context_processors.app_notifications']}}]
WSGI_APPLICATION = 'smart_shrimp_farm.wsgi.application'
DATABASES = {'default': {'ENGINE':'django.db.backends.sqlite3','NAME': BASE_DIR/'db.sqlite3'}}
LANGUAGE_CODE='id-id'; TIME_ZONE='Asia/Jakarta'; USE_I18N=True; USE_TZ=True
STATIC_URL='static/'; STATICFILES_DIRS=[BASE_DIR/'static']
MEDIA_URL='media/'; MEDIA_ROOT=BASE_DIR/'media'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
LOGIN_URL='/accounts/login/'; LOGIN_REDIRECT_URL='/dashboard/'; LOGOUT_REDIRECT_URL='/'
EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend'
OLLAMA_URL=os.environ.get('OLLAMA_URL','http://localhost:11434')
OLLAMA_MODEL=os.environ.get('OLLAMA_MODEL','gemma2:2b')
FARM_LAT=float(os.environ.get('FARM_LAT','-5.98'))
FARM_LON=float(os.environ.get('FARM_LON','107.02'))
