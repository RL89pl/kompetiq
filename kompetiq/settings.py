"""Ustawienia projektu KompetIQ.

Konfiguracja wyłącznie przez zmienne środowiskowe (plik .env w docker compose).
Lokalnie bez DB_ENGINE używany jest SQLite.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return os.environ.get(name, '1' if default else '0').lower() in ('1', 'true', 'yes')


def env_list(name, default=''):
    return [v.strip() for v in os.environ.get(name, default).split(',') if v.strip()]


DEBUG = env_bool('DJANGO_DEBUG', default=False)
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY') or (
    'dev-insecure-key-tylko-lokalnie' if DEBUG else None
)
if not SECRET_KEY:
    raise RuntimeError('Ustaw DJANGO_SECRET_KEY (lub DJANGO_DEBUG=1 lokalnie).')

ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost')
CSRF_TRUSTED_ORIGINS = env_list('DJANGO_CSRF_TRUSTED_ORIGINS', 'http://localhost:5173')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'drf_spectacular',
    'simple_history',
    'apps.institutions',
    'apps.employees',
    'apps.competencies',
    'apps.assessments',
    'apps.development',
    'apps.deadlines',
    'apps.assistant',
    'apps.documents',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
    'apps.institutions.middleware.InstitutionMiddleware',
]

ROOT_URLCONF = 'kompetiq.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'kompetiq.wsgi.application'

if os.environ.get('DB_ENGINE') == 'django.db.backends.postgresql':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME', 'kompetiq'),
            'USER': os.environ.get('DB_USER', 'kompetiq'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'db'),
            'PORT': os.environ.get('DB_PORT', '5432'),
            'CONN_MAX_AGE': 60,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pl'
TIME_ZONE = 'Europe/Warsaw'
USE_I18N = True
USE_TZ = True

# Pliki statyczne i media serwuje nginx na hoście z katalogu ./public
# SERVE_STATIC=1 — Django sam serwuje /static/ (lokalnie, bez nginx na hoście). Na serwerze: 0, serwuje nginx.
SERVE_STATIC = env_bool('SERVE_STATIC', default=False)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'public' / 'static'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'public' / 'media'

# Zbudowany frontend (vite build -> frontend/dist, base=/static/spa/)
FRONTEND_DIST = BASE_DIR / 'frontend' / 'dist'
STATICFILES_DIRS = [('spa', FRONTEND_DIST)] if FRONTEND_DIST.exists() else []

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Za nginx na hoście
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
COOKIE_SECURE = env_bool('COOKIE_SECURE', default=not DEBUG)
SESSION_COOKIE_SECURE = COOKIE_SECURE
CSRF_COOKIE_SECURE = COOKIE_SECURE
SESSION_COOKIE_AGE = 60 * 60 * 8
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '0'))  # włącz po potwierdzeniu, że całość działa po HTTPS
X_FRAME_OPTIONS = 'DENY'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
        'apps.institutions.permissions.HasInstitution',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_RATES': {'assistant': os.environ.get('ASSISTANT_RATE', '60/hour')},
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'KompetIQ API',
    'DESCRIPTION': (
        'API KompetIQ (Kompas Kompetencji) — to samo, z którego korzysta interfejs. Przeznaczone do integracji '
        'z systemami kadrowymi (np. QNT: pracownicy, komórki, opisy stanowisk) i EZD (eksport arkuszy PDF).\n\n'
        '**Uwierzytelnianie:** sesja Django. `GET /api/v1/auth/csrf/` → `POST /api/v1/auth/login/`; '
        'żądania zmieniające dane wymagają nagłówka `X-CSRFToken`. Wszystkie dane są ograniczone do aktywnej '
        'instytucji użytkownika i jego roli. Integracje systemowe: token/OAuth2 do dodania przed wdrożeniem '
        '(docs/04_bezpieczenstwo_i_wdrozenie.md).\n\n'
        '**AI:** odpowiedzi funkcji asystenta są sugestiami — nie zawierają ocen ani poziomów; ocenę ustala przełożony.'
    ),
    'VERSION': '1.0.0',
    'COMPONENT_SPLIT_REQUEST': True,
    'ENUM_NAME_OVERRIDES': {
        'AssessmentStatusEnum': 'apps.assessments.models.Status',
        'AssessmentResultEnum': 'apps.assessments.models.Result',
        'DevelopmentActionStatusEnum': 'apps.development.models.DevelopmentAction.Status',
    },
}

# Asystent AI — dostawca wybierany konfiguracją (patrz apps/assistant/client.py)
#   openai_compat: Groq / Gemini / Mistral / OpenRouter / vLLM (PLLuM) / Ollama (Bielik)
#   anthropic:     Claude API
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')
LLM_BASE_URL = os.environ.get('LLM_BASE_URL', '')
LLM_API_KEY = os.environ.get('LLM_API_KEY', '')
LLM_MODEL = os.environ.get('LLM_MODEL', '')
LLM_JSON_MODE = os.environ.get('LLM_JSON_MODE', 'json_object')  # json_schema | json_object | prompt
ASSISTANT_PROVIDER = os.environ.get(
    'ASSISTANT_PROVIDER', 'openai_compat' if LLM_BASE_URL else ('anthropic' if ANTHROPIC_API_KEY else ''))
ASSISTANT_MODEL = os.environ.get('ASSISTANT_MODEL', 'claude-opus-5-5')
ASSISTANT_ENABLED = env_bool('ASSISTANT_ENABLED', default=bool(ASSISTANT_PROVIDER))
# Minimalny wynik dopasowania źródeł — poniżej asystent formalny odpowiada „brak informacji w bazie wiedzy”
# Łączny limit znaków źródeł przekazywanych modelowi (≈ 3 znaki/token) i limit długości odpowiedzi
ASSISTANT_CONTEXT_CHARS = int(os.environ.get('ASSISTANT_CONTEXT_CHARS', '9000'))
LLM_MAX_TOKENS = int(os.environ.get('LLM_MAX_TOKENS', '4096'))
LLM_TIMEOUT = float(os.environ.get('LLM_TIMEOUT', '120'))
ASSISTANT_MIN_RETRIEVAL_SCORE = float(os.environ.get('ASSISTANT_MIN_RETRIEVAL_SCORE', '2.0'))
# Minimalny udział słów pytania obecnych w jednym źródle (odrzuca pytania spoza tematu z jednym przypadkowym słowem)
ASSISTANT_MIN_COVERAGE = float(os.environ.get('ASSISTANT_MIN_COVERAGE', '0.6'))

LEGAL_DOCS_DIR = BASE_DIR / 'docs_assets'

EMAILLABS_SMTP = os.environ.get('EMAILLABS_SMTP', '')
EMAILLABS_APP_KEY = os.environ.get('EMAILLABS_APP_KEY', '')
EMAILLABS_SECRET_KEY = os.environ.get('EMAILLABS_SECRET_KEY', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'KompetIQ <kontakt@robertlewandowski.dev>')

EMAIL_BACKEND_PATH = os.environ.get(
    'EMAIL_BACKEND',
    'kompetiq.emaillabs.EmailLabsBackend' if EMAILLABS_APP_KEY
    else ('django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend'),
)
if 'emaillabs' in EMAIL_BACKEND_PATH:
    _mail_options = {'smtp_account': EMAILLABS_SMTP, 'app_key': EMAILLABS_APP_KEY,
                     'secret_key': EMAILLABS_SECRET_KEY}
elif 'smtp' in EMAIL_BACKEND_PATH:
    _mail_options = {'host': os.environ.get('EMAIL_HOST', 'localhost'),
                     'port': int(os.environ.get('EMAIL_PORT', '25'))}
else:
    _mail_options = {}
# „default” zapisuje każdy e-mail w skrzynce testowej (kompetiq/mail.py) i przekazuje adresy spoza domen testowych
# do właściwego dostawcy („delivery”). Konta demo mają adresy w domenie .test — ich poczta nigdy nie wychodzi.
MAILERS = {
    'default': {'BACKEND': 'kompetiq.mail.OutboxBackend'},
    'delivery': {'BACKEND': EMAIL_BACKEND_PATH, 'OPTIONS': _mail_options},
}
EMAIL_CAPTURE_DOMAINS = env_list('EMAIL_CAPTURE_DOMAINS', '.test')
# Publiczny adres aplikacji — do linków w e-mailach.
APP_URL = os.environ.get('APP_URL', 'https://kompetiq.devcage.pl').rstrip('/')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': os.environ.get('LOG_LEVEL', 'INFO')},
}
