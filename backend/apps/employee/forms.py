from django import forms

from apps.common.validators import (
    validate_aadhaar,
    validate_ifsc,
    validate_mobile,
    validate_pan,
    validate_uan,
)
from apps.company.models import Branch, Company, Department, Designation

from .models import DocumentType, Employee, EmployeeDocument, SalaryStructure


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = [
            'company', 'branch', 'department', 'designation',
            'employee_code', 'auto_generate_code',
            'first_name', 'last_name', 'email', 'mobile', 'alternate_mobile',
            'date_of_birth', 'gender', 'photo',
            'aadhaar', 'pan', 'uan', 'esic_number',
            'bank_name', 'account_holder_name', 'bank_account_number', 'ifsc_code',
            'salary_structure', 'basic_salary', 'pf_eligible', 'esi_eligible',
            'date_of_joining', 'date_of_exit', 'employment_status',
            'emergency_contact_name', 'emergency_contact_phone', 'emergency_contact_relation',
            'is_active',
        ]
        widgets = {
            'company': forms.Select(attrs={'class': 'form-select', 'id': 'id_company'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'designation': forms.Select(attrs={'class': 'form-select'}),
            'employee_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank for auto code'}),
            'auto_generate_code': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'alternate_mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'aadhaar': forms.TextInput(attrs={'class': 'form-control'}),
            'pan': forms.TextInput(attrs={'class': 'form-control'}),
            'uan': forms.TextInput(attrs={'class': 'form-control'}),
            'esic_number': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_holder_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bank_account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'ifsc_code': forms.TextInput(attrs={'class': 'form-control'}),
            'salary_structure': forms.Select(attrs={'class': 'form-select'}),
            'basic_salary': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'pf_eligible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'esi_eligible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'date_of_joining': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'date_of_exit': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'employment_status': forms.Select(attrs={'class': 'form-select'}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_relation': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = Company.objects.filter(is_active=True).order_by('company_name')
        company = self._resolve_company()
        if company:
            self._filter_company_querysets(company)
        else:
            self.fields['branch'].queryset = Branch.objects.none()
            self.fields['department'].queryset = Department.objects.none()
            self.fields['designation'].queryset = Designation.objects.none()
            self.fields['salary_structure'].queryset = SalaryStructure.objects.none()

    def _resolve_company(self):
        if self.data.get('company'):
            return Company.objects.filter(pk=self.data.get('company')).first()
        if self.instance.pk:
            return self.instance.company
        company_id = self.initial.get('company')
        if company_id:
            return Company.objects.filter(pk=company_id).first()
        return None

    def _filter_company_querysets(self, company):
        self.fields['branch'].queryset = Branch.objects.filter(company=company, is_active=True)
        self.fields['department'].queryset = Department.objects.filter(company=company, is_active=True)
        self.fields['designation'].queryset = Designation.objects.filter(company=company, is_active=True)
        self.fields['salary_structure'].queryset = SalaryStructure.objects.filter(company=company, is_active=True)

    def clean_employee_code(self):
        code = self.cleaned_data.get('employee_code', '').strip().upper()
        auto_generate = self.cleaned_data.get('auto_generate_code', True)
        if not code and auto_generate:
            return ''
        if not code and not auto_generate:
            raise forms.ValidationError('Enter an employee code or enable auto generation.')
        company = self.cleaned_data.get('company')
        if code and company:
            queryset = Employee.all_objects.filter(company=company, employee_code__iexact=code)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError('This employee code is already used in the selected company.')
        return code

    def clean_pan(self):
        pan = self.cleaned_data.get('pan', '')
        if pan:
            validate_pan(pan)
            return pan.strip().upper()
        return pan

    def clean_aadhaar(self):
        aadhaar = self.cleaned_data.get('aadhaar', '')
        if aadhaar:
            validate_aadhaar(aadhaar)
            return ''.join(aadhaar.split())
        return aadhaar

    def clean_uan(self):
        uan = self.cleaned_data.get('uan', '')
        if uan:
            validate_uan(uan)
            return ''.join(uan.split())
        return uan

    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile', '')
        if mobile:
            validate_mobile(mobile)
            return ''.join(mobile.split())
        return mobile

    def clean_alternate_mobile(self):
        mobile = self.cleaned_data.get('alternate_mobile', '')
        if mobile:
            validate_mobile(mobile)
            return ''.join(mobile.split())
        return mobile

    def clean_ifsc_code(self):
        ifsc = self.cleaned_data.get('ifsc_code', '')
        if ifsc:
            validate_ifsc(ifsc)
            return ifsc.strip().upper()
        return ifsc

    def clean(self):
        cleaned_data = super().clean()
        company = cleaned_data.get('company')
        for field_name in ('branch', 'department', 'designation', 'salary_structure'):
            related = cleaned_data.get(field_name)
            if related and company and related.company_id != company.id:
                self.add_error(field_name, f'Selected {field_name} does not belong to the chosen company.')
        return cleaned_data


class EmployeeDocumentForm(forms.ModelForm):
    class Meta:
        model = EmployeeDocument
        fields = ['document_type', 'title', 'file']
        widgets = {
            'document_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class EmployeeImportForm(forms.Form):
    company = forms.ModelChoiceField(
        queryset=Company.objects.filter(is_active=True).order_by('company_name'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    file = forms.FileField(
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.xlsx,.xls'}),
        help_text='Upload an Excel file (.xlsx) using the PAS employee import template.',
    )
