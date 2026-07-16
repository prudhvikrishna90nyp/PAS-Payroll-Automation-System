from django import forms

from apps.clients.models import Client
from apps.common.validators import validate_gstin, validate_pan

from .models import Branch, Company


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
            'tan': forms.TextInput(attrs={'class': 'form-control'}),
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
            'code': forms.TextInput(attrs={'class': 'form-control'}),
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
