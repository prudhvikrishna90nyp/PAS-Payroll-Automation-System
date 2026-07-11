import os

from .base import *  # noqa: F403

DEBUG = os.environ.get('DEBUG', 'True').lower() in {'1', 'true', 'yes'}

STORAGES['staticfiles']['BACKEND'] = 'django.contrib.staticfiles.storage.StaticFilesStorage'  # noqa: F405
