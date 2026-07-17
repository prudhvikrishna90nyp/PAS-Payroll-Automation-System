import re

from django.core.exceptions import ValidationError

PAN_REGEX = re.compile(r'^[A-Z]{5}[0-9]{4}[A-Z]$')
GSTIN_REGEX = re.compile(
    r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$'
)
TAN_REGEX = re.compile(r'^[A-Z]{4}[0-9]{5}[A-Z]$')
AADHAAR_REGEX = re.compile(r'^[0-9]{12}$')
UAN_REGEX = re.compile(r'^[0-9]{12}$')
IFSC_REGEX = re.compile(r'^[A-Z]{4}0[A-Z0-9]{6}$')
MOBILE_REGEX = re.compile(r'^[6-9][0-9]{9}$')


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


def validate_aadhaar(value):
    if not value:
        return
    normalized = re.sub(r'\s+', '', value.strip())
    if not AADHAAR_REGEX.match(normalized):
        raise ValidationError(
            'Enter a valid 12-digit Aadhaar number.',
            code='invalid_aadhaar',
        )


def validate_uan(value):
    if not value:
        return
    normalized = re.sub(r'\s+', '', value.strip())
    if not UAN_REGEX.match(normalized):
        raise ValidationError(
            'Enter a valid 12-digit UAN.',
            code='invalid_uan',
        )


def validate_ifsc(value):
    if not value:
        return
    normalized = value.strip().upper()
    if not IFSC_REGEX.match(normalized):
        raise ValidationError(
            'Enter a valid IFSC code (e.g. SBIN0001234).',
            code='invalid_ifsc',
        )


def validate_mobile(value):
    if not value:
        return
    normalized = re.sub(r'\s+', '', value.strip())
    if not MOBILE_REGEX.match(normalized):
        raise ValidationError(
            'Enter a valid 10-digit Indian mobile number.',
            code='invalid_mobile',
        )
