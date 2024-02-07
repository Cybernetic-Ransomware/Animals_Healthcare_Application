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

import pycouchdb

from decouple import config

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
    "django_cron",
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
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

# COUCH_CONNECTOR = (config("COUCH_CONNECTOR"),)

COUCHDB_USER = config("COUCHDB_USER")
COUCHDB_PASSWORD = config("COUCHDB_PASSWORD")
COUCHDB_PORT = config("COUCHDB_PORT")

COUCH_SERVER = pycouchdb.Server(
    f"http://{COUCHDB_USER}:{COUCHDB_PASSWORD}@appendixes-db:{COUCHDB_PORT}/", authmethod="basic"
)
COUCH_DB = COUCH_SERVER.database("appendixes")

COUCH_DB_LIMIT_PER_NOTE = 5

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
    # ("*/4 * * * *", "AHC_app.celery_notifications.cron.send_emails"),
    # ("*/2 * * * *", "AHC_app.celery_notifications.cron.send_email_example"),
    # # ('2 * * * *', 'AHC_app.celery_notifications.cron:send_emails'),
    # ("4 * * * *", "AHC_app.celery_notifications.cron.send_sms"),
    ("6 * * * *", "AHC_app.celery_notifications.cron.send_discord_notes"),
]

CRON_CLASSES = [
    # 'AHC_app.celery_notifications.cron.SynchNotificationsCron',
]

CELERY_BROKER_URL = config("CELERY_BROKER_URL")
CELERY_BACKEND = config("CELERY_BACKEND")


EMAIL_BACKEND = config("EMAIL_BACKEND")
EMAIL_HOST = config("EMAIL_HOST")
EMAIL_PORT = config("EMAIL_PORT", cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=False, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")

DISCORD_TOKEN = config("DISCORD_TOKEN")
