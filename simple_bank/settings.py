from decimal import Decimal
import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()




BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_KEY")

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',

    'users',
    'transactions',
    'accounts',
    'clients',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'simplebank.urls'

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

WSGI_APPLICATION = 'simplebank.wsgi.application'
AUTH_USER_MODEL = 'users.User'

# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "HOST": os.getenv("DB_HOST"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Local development connects directly, without a trusted reverse proxy.
    "NUM_PROXIES": 0,
    # These limits count all requests per IP, including successful requests.
    # The default local-memory cache is per process; multi-worker deployments
    # need a shared cache. DRF throttling is not a strict concurrent rate limit.
    "DEFAULT_THROTTLE_RATES": {
        "auth_login": "10/minute",
        "auth_register": "5/hour",
        "auth_refresh": "30/minute",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
}



# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "../static/media")


# Email
# https://docs.djangoproject.com/en/6.1/topics/email/#topic-email-configuration

MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}






LOGGING = {
    "version": 1,
    # 'handlers': {
    #     'console': {'class': 'logging.StreamHandler'}
    # },
    # 'loggers': {
    #     'django.db.backends':{
    #         'handlers': ['console'],
    #         'level': 'DEBUG'
    #     }
    # }
    "disable_existing_loggers": False,
    "handlers": {
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "general.log",
            "maxBytes": 1024 * 1024,
            "backupCount": 30,
            "level": "DEBUG",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "": {
            "level": "DEBUG",
            "handlers": ["file"],
        },
    },
    "formatters": {
        "verbose": {
            "format": "{name} {levelname} {asctime} {module} {lineno} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
}


WELCOME_BONUS_AMOUNT = Decimal("10000.00")
CENT = Decimal("0.01")
TRANSFER_FEE_RATE = Decimal("0.025")
MIN_TRANSFER_FEE = Decimal("5.00")
MAX_TRANSFER_AMOUNT = Decimal("500000.00")