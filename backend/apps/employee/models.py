from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse

from apps.common.mixins import SoftDeleteModel
from apps.company.models import Branch, Company, Department, Designation


class EmploymentStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    ON_LEAVE = 'on_leave', 'On Leave'
    RESIGNED = 'resigned', 'Resigned'
    TERMINATED = 'terminated', 'Terminated'
    RETIRED = 'retired', 'Retired'


class EmploymentType(models.TextChoices):
    PERMANENT = 'permanent', 'Permanent'
    CONTRACT = 'contract', 'Contract'
    TEMPORARY = 'temporary', 'Temporary'
    INTERN = 'intern', 'Intern'
    CONSULTANT = 'consultant', 'Consultant'


class Gender(models.TextChoices):
    MALE = 'male', 'Male'
    FEMALE = 'female', 'Female'
    OTHER = 'other', 'Other'


class DocumentType(models.TextChoices):
    AADHAAR = 'aadhaar', 'Aadhaar'
    PAN = 'pan', 'PAN Card'
    APPOINTMENT = 'appointment', 'Appointment Letter'
    RESUME = 'resume', 'Resume'
    EDUCATIONAL = 'educational', 'Educational Certificates'
    BANK_PASSBOOK = 'bank_passbook', 'Bank Passbook'
    PF_FORM = 'pf_form', 'PF Form'
    ESI_CARD = 'esi_card', 'ESI Card'
    OFFER_LETTER = 'offer_letter', 'Offer Letter'
    BANK_PROOF = 'bank_proof', 'Bank Proof'
    OTHER = 'other', 'Other'


class SalaryStructure(SoftDeleteModel):
    """
    Legacy simple salary template (basic / HRA% / transport).

    Sprint 7 component-based masters live in apps.payroll
    (SalaryComponent, SalaryStructure, EmployeeSalaryAssignment).
    """

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='salary_structures',
    )
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20)
    basic_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    hra_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('40.00'),
        help_text='HRA as percentage of basic salary.',
    )
    transport_allowance = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('1600.00'),
    )
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='employee_salarystructure_created_records',
        null=True,
        blank=True,
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='employee_salarystructure_updated_records',
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        ordering = ['company__company_name', 'name']
        unique_together = [['company', 'code']]

    def __str__(self):
        return f'{self.company.company_name} — {self.name}'

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)


class Employee(SoftDeleteModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='employees',
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
    )
    designation = models.ForeignKey(
        Designation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
    )
    employee_code = models.CharField('Employee Code', max_length=20, blank=True)
    auto_generate_code = models.BooleanField(default=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    mobile = models.CharField(max_length=15, blank=True)
    alternate_mobile = models.CharField(max_length=15, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        blank=True,
    )
    photo = models.ImageField(upload_to='employee/photos/', blank=True)
    aadhaar = models.CharField('Aadhaar', max_length=12, blank=True)
    pan = models.CharField('PAN', max_length=10, blank=True)
    uan = models.CharField('UAN', max_length=12, blank=True)
    esic_number = models.CharField('ESIC Number', max_length=20, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=30, blank=True)
    ifsc_code = models.CharField('IFSC', max_length=11, blank=True)
    account_holder_name = models.CharField(max_length=100, blank=True)
    salary_structure = models.ForeignKey(
        SalaryStructure,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees',
    )
    basic_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    pf_eligible = models.BooleanField('PF Eligible', default=True)
    esi_eligible = models.BooleanField('ESI Eligible', default=False)
    date_of_joining = models.DateField()
    date_of_exit = models.DateField(null=True, blank=True)
    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.PERMANENT,
    )
    employment_status = models.CharField(
        max_length=20,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.ACTIVE,
    )
    emergency_contact_name = models.CharField(max_length=100, blank=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True)
    emergency_contact_relation = models.CharField(max_length=50, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='employee_employee_created_records',
        null=True,
        blank=True,
        editable=False,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='employee_employee_updated_records',
        null=True,
        blank=True,
        editable=False,
    )

    class Meta:
        db_table = 'employees_employee'
        ordering = ['company__company_name', 'employee_code']
        unique_together = [['company', 'employee_code']]
        indexes = [
            models.Index(fields=['employee_code'], name='employee_code_idx'),
            models.Index(fields=['employment_status'], name='employee_status_idx'),
        ]

    def __str__(self):
        return f'{self.employee_code} - {self.full_name}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def employee_id(self):
        return self.employee_code

    def get_absolute_url(self):
        return reverse('employees:employee_detail', kwargs={'pk': self.pk})

    def save(self, *args, **kwargs):
        self.first_name = self.first_name.strip()
        if self.last_name:
            self.last_name = self.last_name.strip()
        if self.email:
            self.email = self.email.strip().lower()
        if self.pan:
            self.pan = self.pan.strip().upper()
        if self.ifsc_code:
            self.ifsc_code = self.ifsc_code.strip().upper()
        if self.aadhaar:
            self.aadhaar = ''.join(self.aadhaar.split())
        if self.employee_code:
            self.employee_code = self.employee_code.strip().upper()
        elif self.auto_generate_code and self.company_id:
            from .services import generate_employee_code

            self.employee_code = generate_employee_code(self.company)
        super().save(*args, **kwargs)


class EmployeeDocument(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='documents',
    )
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
    )
    title = models.CharField(max_length=200, blank=True)
    file = models.FileField(upload_to='employee/documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title or self.get_document_type_display()
