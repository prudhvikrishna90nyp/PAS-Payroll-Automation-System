from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError
from django.forms import inlineformset_factory

from apps.company.models import Company
from apps.employee.models import Employee

from .models import (
    EmployeeSalaryAssignment,
    PayrollPeriod,
    PayrollPeriodStatus,
    PayrollRun,
    SalaryComponent,
    SalaryStructure,
    SalaryStructureLine,
)
from .seed import seed_standard_components
from .services.validation import (
    validate_assignment,
    validate_component,
    validate_payroll_period,
    validate_structure,
)


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'form-select')
            elif isinstance(widget, forms.Textarea):
                widget.attrs.setdefault('class', 'form-control')
                widget.attrs.setdefault('rows', 3)
            else:
                widget.attrs.setdefault('class', 'form-control')


class SalaryComponentForm(BootstrapModelForm):
    class Meta:
        model = SalaryComponent
        fields = [
            'company',
            'component_code',
            'component_name',
            'component_type',
            'calculation_type',
            'formula',
            'taxable',
            'pf_applicable',
            'esi_applicable',
            'include_in_ctc',
            'include_in_gross',
            'rounding_rule',
            'display_order',
            'is_active',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = Company.objects.filter(is_active=True).order_by(
            'company_name'
        )

    def clean(self):
        cleaned = super().clean()
        instance = SalaryComponent(**{**cleaned, 'pk': self.instance.pk})
        errors = validate_component(instance)
        if errors:
            raise DjangoValidationError(errors)
        return cleaned


class SalaryStructureForm(BootstrapModelForm):
    class Meta:
        model = SalaryStructure
        fields = ['company', 'name', 'code', 'description', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = Company.objects.filter(is_active=True).order_by(
            'company_name'
        )


class SalaryStructureLineForm(BootstrapModelForm):
    class Meta:
        model = SalaryStructureLine
        fields = [
            'component',
            'calculation_type',
            'value',
            'percent',
            'formula_override',
            'display_order',
        ]

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        qs = SalaryComponent.objects.filter(is_active=True)
        if company is not None:
            qs = qs.filter(company=company)
        elif self.instance and self.instance.structure_id:
            qs = qs.filter(company=self.instance.structure.company)
        self.fields['component'].queryset = qs.order_by('display_order', 'component_code')
        self.fields['calculation_type'].required = False


SalaryStructureLineFormSet = inlineformset_factory(
    SalaryStructure,
    SalaryStructureLine,
    form=SalaryStructureLineForm,
    extra=3,
    can_delete=True,
)


class EmployeeSalaryAssignmentForm(BootstrapModelForm):
    class Meta:
        model = EmployeeSalaryAssignment
        fields = [
            'employee',
            'salary_structure',
            'effective_from',
            'effective_to',
            'gross_salary',
            'ctc',
            'remarks',
            'is_active',
        ]
        widgets = {
            'effective_from': forms.DateInput(attrs={'type': 'date'}),
            'effective_to': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = Employee.objects.filter(is_active=True).order_by(
            'employee_code'
        )
        self.fields['salary_structure'].queryset = SalaryStructure.objects.filter(
            is_active=True
        ).order_by('company__company_name', 'name')
        self.fields['ctc'].required = False
        self.fields['effective_to'].required = False

    def clean(self):
        cleaned = super().clean()
        instance = self.instance
        for field in (
            'employee',
            'salary_structure',
            'effective_from',
            'effective_to',
            'gross_salary',
            'ctc',
            'remarks',
            'is_active',
        ):
            if field in cleaned:
                setattr(instance, field, cleaned[field])
        if instance.ctc in (None, ''):
            instance.ctc = Decimal('0.00')
            cleaned['ctc'] = instance.ctc
        errors = validate_assignment(instance)
        # Soft-close path: allow overlap with open-ended current assignment
        filtered = [
            e for e in errors
            if 'Overlaps existing assignment' not in e
        ]
        if instance.salary_structure_id:
            filtered = [
                e for e in filtered
                if not e.startswith('Missing mandatory') and 'at least one component' not in e
            ] + [
                e for e in validate_structure(instance.salary_structure)
                if e.startswith('Circular') or 'invalid percentage' in e.lower()
                or 'cannot be negative' in e.lower()
            ]
        # Re-run full structure validation for create when lines exist
        if instance.salary_structure_id and instance.salary_structure.lines.exists():
            struct_errors = validate_structure(instance.salary_structure)
            for err in struct_errors:
                if err not in filtered:
                    filtered.append(err)
        if filtered:
            raise DjangoValidationError(filtered)
        return cleaned


class SeedComponentsForm(forms.Form):
    company = forms.ModelChoiceField(
        queryset=Company.objects.filter(is_active=True).order_by('company_name'),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    def save(self, user=None):
        return seed_standard_components(self.cleaned_data['company'], user=user)


class PayrollPeriodForm(BootstrapModelForm):
    class Meta:
        model = PayrollPeriod
        fields = ['company', 'month', 'year', 'start_date', 'end_date', 'status']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = Company.objects.filter(is_active=True).order_by(
            'company_name'
        )
        if not self.instance.pk:
            self.fields['status'].initial = PayrollPeriodStatus.OPEN

    def clean(self):
        cleaned = super().clean()
        instance = PayrollPeriod(
            pk=self.instance.pk,
            company=cleaned.get('company'),
            month=cleaned.get('month'),
            year=cleaned.get('year'),
            start_date=cleaned.get('start_date'),
            end_date=cleaned.get('end_date'),
            status=cleaned.get('status') or PayrollPeriodStatus.OPEN,
        )
        errors = validate_payroll_period(instance)
        if errors:
            raise DjangoValidationError(errors)
        return cleaned


class PayrollRunForm(BootstrapModelForm):
    class Meta:
        model = PayrollRun
        fields = ['period', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['period'].queryset = (
            PayrollPeriod.objects
            .filter(status=PayrollPeriodStatus.OPEN)
            .select_related('company')
            .order_by('-year', '-month')
        )
        self.fields['notes'].required = False
