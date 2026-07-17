from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.clients.models import Client
from apps.common.mixins import SoftDeleteModel


class Company(SoftDeleteModel):
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name='companies',
    )
    company_name = models.CharField(max_length=200)
    trade_name = models.CharField(max_length=200, blank=True)
    pan = models.CharField('PAN', max_length=10, blank=True)
    gstin = models.CharField('GSTIN', max_length=15, blank=True)
    tan = models.CharField('TAN', max_length=10, blank=True)
    epf_code = models.CharField('EPF Code', max_length=50, blank=True)
    esi_code = models.CharField('ESI Code', max_length=50, blank=True)
    professional_tax_registration = models.CharField(
        'Professional Tax Registration',
        max_length=50,
        blank=True,
    )
    labour_licence = models.CharField('Labour Licence', max_length=50, blank=True)
    address = models.TextField(blank=True)
    state = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    pin_code = models.CharField('PIN Code', max_length=10, blank=True)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    logo = models.ImageField(upload_to='company/logos/', blank=True)
    bank_details = models.TextField(
        'Bank Details',
        blank=True,
        help_text='Bank name, account number, IFSC, branch, etc.',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='company_company_created_records',
        null=True,
        blank=True,
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='company_company_updated_records',
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'
        ordering = ['company_name']
        indexes = [
            models.Index(fields=['company_name'], name='company_name_idx'),
            models.Index(fields=['pan'], name='company_pan_idx'),
            models.Index(fields=['gstin'], name='company_gstin_idx'),
        ]

    def __str__(self):
        return self.company_name

    def get_absolute_url(self):
        return reverse('company:company_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        self.company_name = self.company_name.strip()
        if self.trade_name:
            self.trade_name = self.trade_name.strip()
        if self.pan:
            self.pan = self.pan.strip().upper()
        if self.gstin:
            self.gstin = self.gstin.strip().upper()
        if self.tan:
            self.tan = self.tan.strip().upper()
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


class Branch(SoftDeleteModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='branches',
    )
    branch_name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    state = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    pin_code = models.CharField('PIN Code', max_length=10, blank=True)
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_head_office = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Branches'
        ordering = ['company__company_name', 'branch_name']
        unique_together = [['company', 'code']]

    def __str__(self):
        return f'{self.company.company_name} — {self.branch_name}'
