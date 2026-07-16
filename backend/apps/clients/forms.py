from django import forms

from .models import Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = [
            'client_code',
            'client_name',
            'trade_name',
            'contact_person',
            'mobile',
            'alternate_mobile',
            'email',
            'pan',
            'gstin',
            'address_line_1',
            'address_line_2',
            'city',
            'district',
            'state',
            'pincode',
            'notes',
            'is_active',
        ]
        widgets = {
            'client_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Example: CLI001',
            }),
            'client_name': forms.TextInput(attrs={'class': 'form-control'}),
            'trade_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '10',
            }),
            'alternate_mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '10',
            }),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'pan': forms.TextInput(attrs={
                'class': 'form-control text-uppercase',
                'maxlength': '10',
                'placeholder': 'ABCDE1234F',
            }),
            'gstin': forms.TextInput(attrs={
                'class': 'form-control text-uppercase',
                'maxlength': '15',
            }),
            'address_line_1': forms.TextInput(attrs={'class': 'form-control'}),
            'address_line_2': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'district': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'pincode': forms.TextInput(attrs={
                'class': 'form-control',
                'maxlength': '6',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_client_code(self):
        return self.cleaned_data['client_code'].strip().upper()

    def clean_pan(self):
        value = self.cleaned_data.get('pan', '')
        return value.strip().upper()

    def clean_gstin(self):
        value = self.cleaned_data.get('gstin', '')
        return value.strip().upper()

    def clean_email(self):
        value = self.cleaned_data.get('email', '')
        return value.strip().lower()
