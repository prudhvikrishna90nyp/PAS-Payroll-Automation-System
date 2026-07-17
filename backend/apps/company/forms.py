from django import forms

from apps.clients.models import Client
from apps.common.validators import validate_gstin, validate_pan, validate_tan

from .models import Branch, Company, Department, Designation


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            'client', 'company_name', 'trade_name', 'logo', 'pan', 'gstin', 'tan',
            'epf_code', 'esi_code', 'professional_tax_registration', 'labour_licence',
            'address', 'state', 'district', 'pin_code',
            'contact_person', 'phone', 'email', 'bank_details', 'is_active',
        ]
        widgets = {
            'client': forms.Select(attrs={'class': 'form-select'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'trade_name': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'pan': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABCDE1234F'}),
            'gstin': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '15-character GSTIN'}),
            'tan': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABCD12345E'}),
            'epf_code': forms.TextInput(attrs={'class': 'form-control'}),
            'esi_code': forms.TextInput(attrs={'class': 'form-control'}),
            'professional_tax_registration': forms.TextInput(attrs={'class': 'form-control'}),
            'labour_licence': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'district': forms.TextInput(attrs={'class': 'form-control'}),
            'pin_code': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'bank_details': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].queryset = Client.objects.filter(is_active=True).order_by('client_name')

    def clean_pan(self):
        pan = self.cleaned_data.get('pan', '')
        if pan:
            validate_pan(pan)
            return pan.strip().upper()
        return pan

    def clean_gstin(self):
        gstin = self.cleaned_data.get('gstin', '')
        if gstin:
            validate_gstin(gstin)
            return gstin.strip().upper()
        return gstin

    def clean_tan(self):
        tan = self.cleaned_data.get('tan', '')
        if tan:
            validate_tan(tan)
            return tan.strip().upper()
        return tan


class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = [
            'company', 'branch_name', 'code', 'address', 'state', 'district', 'pin_code',
            'contact_person', 'phone', 'email', 'is_head_office', 'is_active',
        ]
        widgets = {
            'company': forms.Select(attrs={'class': 'form-select'}),
            'branch_name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unique within company'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'district': forms.TextInput(attrs={'class': 'form-control'}),
            'pin_code': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_head_office': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = Company.objects.filter(is_active=True).order_by('company_name')

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        if not code:
            raise forms.ValidationError('Branch code is required.')
        company = self.cleaned_data.get('company')
        if company:
            queryset = Branch.all_objects.filter(company=company, code__iexact=code)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError('This code is already used for the selected company.')
        return code


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['company', 'name', 'code', 'description', 'is_active']
        widgets = {
            'company': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unique within company'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = Company.objects.filter(is_active=True).order_by('company_name')

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        if not code:
            raise forms.ValidationError('Department code is required.')
        company = self.cleaned_data.get('company')
        if company:
            queryset = Department.all_objects.filter(company=company, code__iexact=code)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError('This code is already used for the selected company.')
        return code


class DesignationForm(forms.ModelForm):
    class Meta:
        model = Designation
        fields = ['company', 'name', 'code', 'description', 'is_active']
        widgets = {
            'company': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Unique within company'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = Company.objects.filter(is_active=True).order_by('company_name')

    def clean_code(self):
        code = self.cleaned_data.get('code', '').strip().upper()
        if not code:
            raise forms.ValidationError('Designation code is required.')
        company = self.cleaned_data.get('company')
        if company:
            queryset = Designation.all_objects.filter(company=company, code__iexact=code)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError('This code is already used for the selected company.')
        return code
