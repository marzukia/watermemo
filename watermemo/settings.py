from __future__ import annotations

from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY", default="change-me-in-production")

DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1",
    cast=lambda v: [h.strip() for h in v.split(",") if h.strip()],
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    # local
    "core",
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

ROOT_URLCONF = "watermemo.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "watermemo.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="watermemo"),
        "USER": config("DB_USER", default="watermemo"),
        "PASSWORD": config("DB_PASSWORD", default="postgres"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        )
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": ("django.contrib.auth.password_validation.CommonPasswordValidator")},
    {"NAME": ("django.contrib.auth.password_validation.NumericPasswordValidator")},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# LLM settings (override in .env)
LLM_BASE_URL = config("LLM_BASE_URL", default="http://localhost:11434/v1")
LLM_API_KEY = config("LLM_API_KEY", default="ollama")
LLM_MODEL = config("LLM_MODEL", default="gemma3:latest")
LLM_EMBEDDING_MODEL = config("LLM_EMBEDDING_MODEL", default="nomic-embed-text")

# Separate embedding endpoint (falls back to LLM_BASE_URL if unset).
LLM_EMBED_BASE_URL = config("LLM_EMBED_BASE_URL", default="")
LLM_EMBED_API_KEY = config("LLM_EMBED_API_KEY", default="")
