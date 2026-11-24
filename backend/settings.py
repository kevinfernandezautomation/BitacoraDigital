import os
from pathlib import Path
BASE_DIR=Path(__file__).parent
DEBUG=os.getenv('DEBUG','0')=='1'
SECRET_KEY=os.environ['SECRET_KEY']
ALLOWED_HOSTS=os.getenv('ALLOWED_HOSTS','localhost,127.0.0.1').split(',')
INSTALLED_APPS=['django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','core']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
DATABASES={'default':{'ENGINE':'django.db.backends.postgresql','NAME':os.getenv('POSTGRES_DB','ciqpa'),'USER':os.getenv('POSTGRES_USER','ciqpa'),'PASSWORD':os.environ['POSTGRES_PASSWORD'],'HOST':os.getenv('DB_HOST','db'),'PORT':'5432'}}
if os.getenv('SQLITE')=='1': DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3'}}
AUTH_USER_MODEL='core.User'
AUTH_PASSWORD_VALIDATORS=[{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':12}},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'}]
PASSWORD_HASHERS=['django.contrib.auth.hashers.Argon2PasswordHasher','django.contrib.auth.hashers.PBKDF2PasswordHasher']
LANGUAGE_CODE='es'; TIME_ZONE='America/Costa_Rica'; USE_TZ=True
STATIC_URL='/static/'; STATIC_ROOT=BASE_DIR/'collected'; STATICFILES_DIRS=[BASE_DIR/'static']; MEDIA_ROOT=BASE_DIR/'private'
LOGIN_URL='/login/'; LOGIN_REDIRECT_URL='/'; LOGOUT_REDIRECT_URL='/login/'
SESSION_COOKIE_SECURE=not DEBUG; CSRF_COOKIE_SECURE=not DEBUG; SECURE_SSL_REDIRECT=not DEBUG; SECURE_CONTENT_TYPE_NOSNIFF=True; X_FRAME_OPTIONS='DENY'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
EMAIL_BACKEND=os.getenv('EMAIL_BACKEND','django.core.mail.backends.console.EmailBackend')
EMAIL_HOST=os.getenv('EMAIL_HOST','localhost'); EMAIL_PORT=int(os.getenv('EMAIL_PORT','587')); EMAIL_USE_TLS=True
EMAIL_HOST_USER=os.getenv('EMAIL_HOST_USER',''); EMAIL_HOST_PASSWORD=os.getenv('EMAIL_HOST_PASSWORD',''); DEFAULT_FROM_EMAIL=os.getenv('DEFAULT_FROM_EMAIL','bitacora@example.invalid')

ALLOW_UNSIGNED_CLOSE=DEBUG and os.getenv("ALLOW_UNSIGNED_CLOSE","0")=="1"
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE="Lax"
CSRF_COOKIE_SAMESITE="Lax"
SESSION_COOKIE_AGE=1800
SECURE_HSTS_SECONDS=0 if DEBUG else 31536000
DATA_UPLOAD_MAX_MEMORY_SIZE=2*1024*1024
FILE_UPLOAD_MAX_MEMORY_SIZE=2*1024*1024
LOGIN_WINDOW=int(os.getenv('LOGIN_WINDOW','300'))
LOGIN_IP_LIMIT=int(os.getenv('LOGIN_IP_LIMIT','60'))
LOGIN_PAIR_LIMIT=int(os.getenv('LOGIN_PAIR_LIMIT','5'))
MIDDLEWARE.insert(MIDDLEWARE.index('django.contrib.auth.middleware.AuthenticationMiddleware')+1,'core.authentication.IdleSessionMiddleware')
SECURE_REFERRER_POLICY='same-origin'
# Safe defaults: no real delivery until explicitly enabled; no console disclosure.
EMAIL_BACKEND=os.getenv('EMAIL_BACKEND','django.core.mail.backends.locmem.EmailBackend')
EMAIL_TIMEOUT=15
SHEET_EMAIL_ENABLED=os.getenv('SHEET_EMAIL_ENABLED','0')=='1'
SHEET_EMAIL_MAX_BYTES=int(os.getenv('SHEET_EMAIL_MAX_BYTES','15000000'))
SHEET_EMAIL_HOURLY_LIMIT=int(os.getenv('SHEET_EMAIL_HOURLY_LIMIT','10'))
SHEET_EMAIL_MESSAGE_DOMAIN=os.getenv('SHEET_EMAIL_MESSAGE_DOMAIN','example.invalid')

# V12: only enable proxy trust behind the isolated, header-overwriting gateway.
from django.core.exceptions import ImproperlyConfigured
if os.getenv('TRUST_TLS_PROXY','0') == '1':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
if not DEBUG and (len(SECRET_KEY) < 50 or SECRET_KEY.startswith('replace-')):
    raise ImproperlyConfigured('SECRET_KEY de producción debe ser aleatoria y de al menos 50 caracteres')
AUTH_PASSWORD_VALIDATORS += [
    {'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
MIDDLEWARE.append('core.security.SecurityHeaders')
