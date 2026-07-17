import re

from django.core.exceptions import ValidationError

PAN_REGEX = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
GSTIN_REGEX = re.compile(
    r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$'
)
TAN_REGEX = re.compile(r'^[A-Z]{4}[0-9]{5}[A-Z]$')


def validate_pan(value):
    if not value:
        return
    normalized = value.strip().upper()
    if not PAN_REGEX.match(normalized):
        raise ValidationError(
            'Enter a valid PAN (e.g. ABCDE1234F).',
            code='invalid_pan',
        )


def validate_gstin(value):
    if not value:
        return
    normalized = value.strip().upper()
    if len(normalized) != 15 or not GSTIN_REGEX.match(normalized):
        raise ValidationError(
            'Enter a valid 15-character GSTIN.',
            code='invalid_gstin',
        )


def validate_tan(value):
    if not value:
        return
    normalized = value.strip().upper()
    if not TAN_REGEX.match(normalized):
        raise ValidationError(
            'Enter a valid TAN (e.g. ABCD12345E).',
            code='invalid_tan',
        )
