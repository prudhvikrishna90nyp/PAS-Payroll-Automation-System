from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='%(app_label)s_%(class)s_created_records',
        null=True,
        blank=True,
        editable=False,
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='%(app_label)s_%(class)s_updated_records',
        null=True,
        blank=True,
        editable=False,
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


pan_validator = RegexValidator(
    regex=r'^[A-Z]{5}[0-9]{4}[A-Z]$',
    message='Enter a valid PAN in the format ABCDE1234F.',
)

gstin_validator = RegexValidator(
    regex=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$',
    message='Enter a valid 15-character GSTIN.',
)

mobile_validator = RegexValidator(
    regex=r'^[6-9][0-9]{9}$',
    message='Enter a valid 10-digit Indian mobile number.',
)

pincode_validator = RegexValidator(
    regex=r'^[1-9][0-9]{5}$',
    message='Enter a valid 6-digit PIN code.',
)


class Client(BaseModel):
    client_code = models.CharField(
        max_length=20,
        unique=True,
        help_text='Example: CLI001',
    )

    client_name = models.CharField(max_length=200)

    trade_name = models.CharField(max_length=200, blank=True)

    contact_person = models.CharField(max_length=150, blank=True)

    mobile = models.CharField(max_length=10, validators=[mobile_validator])

    alternate_mobile = models.CharField(
        max_length=10,
        validators=[mobile_validator],
        blank=True,
    )

    email = models.EmailField(blank=True)

    pan = models.CharField(max_length=10, validators=[pan_validator], blank=True)

    gstin = models.CharField(max_length=15, validators=[gstin_validator], blank=True)

    address_line_1 = models.CharField(max_length=250)

    address_line_2 = models.CharField(max_length=250, blank=True)

    city = models.CharField(max_length=100)

    district = models.CharField(max_length=100, blank=True)

    state = models.CharField(max_length=100)

    pincode = models.CharField(max_length=6, validators=[pincode_validator])

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['client_name']
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'
        indexes = [
            models.Index(fields=['client_name'], name='client_name_idx'),
            models.Index(fields=['client_code'], name='client_code_idx'),
            models.Index(fields=['gstin'], name='client_gstin_idx'),
        ]

    def __str__(self):
        return f'{self.client_code} - {self.client_name}'

    def get_absolute_url(self):
        return reverse('clients:client_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        self.client_code = self.client_code.strip().upper()
        self.client_name = self.client_name.strip()

        if self.pan:
            self.pan = self.pan.strip().upper()

        if self.gstin:
            self.gstin = self.gstin.strip().upper()

        if self.email:
            self.email = self.email.strip().lower()

        super().save(*args, **kwargs)
