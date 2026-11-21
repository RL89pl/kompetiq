import os

os.environ.setdefault('DJANGO_SECRET_KEY', 'test-only-secret')
os.environ.setdefault('ASSISTANT_ENABLED', '0')

from .settings import *  # noqa: E402,F401,F403

PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {'assistant': '1000/min'}  # noqa: F405
