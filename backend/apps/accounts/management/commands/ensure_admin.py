"""Create a Django superuser from env vars when missing (Docker-friendly)."""

from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        'Create a superuser if DJANGO_SUPERUSER_USERNAME, '
        'DJANGO_SUPERUSER_EMAIL, and DJANGO_SUPERUSER_PASSWORD are all set. '
        'No-op if the username already exists (does not reset password).'
    )

    def handle(self, *args, **options):
        username = (os.environ.get('DJANGO_SUPERUSER_USERNAME') or '').strip()
        email = (os.environ.get('DJANGO_SUPERUSER_EMAIL') or '').strip()
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD') or ''

        if not username or not email or not password:
            raise CommandError(
                'Set DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL, and '
                'DJANGO_SUPERUSER_PASSWORD to create an admin non-interactively. '
                'Otherwise use: python manage.py createsuperuser'
            )

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(
                f'Superuser "{username}" already exists — skipping.'
            ))
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'Created superuser "{username}".'))
