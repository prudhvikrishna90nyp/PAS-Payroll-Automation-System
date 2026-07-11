from django.db import models


class Company(models.Model):
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
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'
        ordering = ['company_name']

    def __str__(self):
        return self.company_name
