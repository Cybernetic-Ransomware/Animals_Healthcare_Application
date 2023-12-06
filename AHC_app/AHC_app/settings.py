"""
Django's settings for AHC_app project.

Generated by 'django-admin startproject' using Django 4.2.1.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""
import os
from pathlib import Path

from couchdb import Server

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-x#q0@altnjw2yrhh)edi)co2)n3p8q&0qmz7m8oxu-*jhd8d9-"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "crispy_forms",
    "crispy_bootstrap4",
    "bootstrap_modal_forms",
    "compressor",
    "taggit",
    "django_crontab",
    "homepage.apps.HomepageConfig",
    "users.apps.UsersConfig",
    "animals.apps.AnimalsConfig",
    "medical_notes.apps.MedicalNotesConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "AHC_app.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # 'DIRS': [],
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap4"
CRISPY_TEMPLATE_PACK = "bootstrap4"


WSGI_APPLICATION = "AHC_app.wsgi.application"


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    # 'default': {
    #     'ENGINE': 'django.db.backends.sqlite3',
    #     'NAME': BASE_DIR / 'db.sqlite3',
    # },
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "ahc_db",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "postgres_db",
        "PORT": "5432",
    }
}
# PostgreSQL
# drop owned by adr_controller


COUCH_CONNECTOR = Server("http://127.0.0.1:5984")


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LOGIN_REDIRECT_URL = "Homepage"

LOGIN_URL = "login"


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Europe/Warsaw"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = "static_collected"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static/"),
]

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
]

COMPRESS_ROOT = STATIC_ROOT
COMPRESS_PRECOMPILERS = (("text/x-scss", "django_libsass.SassCompiler"),)
COMPRESS_OFFLINE = True
LIBSASS_OUTPUT_STYLE = "compressed"
STATICFILES_STORAGE = "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"

""" DOCUMENTATION TO CUSTOM SCSS:
https://picocss.com/docs/customization.html
https://www.accordbox.com/blog/how-use-scss-sass-your-django-project-python-way/

commands:
python manage.py collectstatic
python manage.py compress --force
"""

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "static/media")

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


CRONJOBS = [
    # ('*/2 * * * *', 'AHC_app.celery_notifications.cron.send_emails'),
    ('*/2 * * * *', 'AHC_app.celery_notifications.cron.send_email_example'),
    # ('2 * * * *', 'AHC_app.celery_notifications.cron:send_emails'),
    ('4 * * * *', 'AHC_app.celery_notifications.cron.send_sms'),
    ('6 * * * *', 'AHC_app.celery_notifications.cron.send_discord_notes')

]

CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_BACKEND = 'redis://redis:6379/0'

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "amtak97@gmail.com"
EMAIL_HOST_PASSWORD = "pmkf yrpz hari mwfj"
