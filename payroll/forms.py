from django import forms
from .models import Employee, PayrollPeriod, PayrollRecord


class DateInput(forms.DateInput):
    input_type = 'date'


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = ['employee_code', 'name', 'position', 'phone', 'bank_name', 'bank_account', 'join_date', 'employment_status', 'pay_type', 'base_salary', 'daily_rate', 'notes']
        widgets = {'join_date': DateInput(), 'notes': forms.Textarea(attrs={'rows': 3})}


class PayrollPeriodForm(forms.ModelForm):
    class Meta:
        model = PayrollPeriod
        fields = ['name', 'start_date', 'end_date', 'payment_date', 'status', 'notes']
        widgets = {'start_date': DateInput(), 'end_date': DateInput(), 'payment_date': DateInput(), 'notes': forms.Textarea(attrs={'rows': 3})}

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('start_date') and cleaned.get('end_date') and cleaned['end_date'] < cleaned['start_date']:
            self.add_error('end_date', 'Tanggal selesai tidak boleh sebelum tanggal mulai.')
        return cleaned


class PayrollRecordForm(forms.ModelForm):
    class Meta:
        model = PayrollRecord
        fields = ['employee', 'work_days', 'base_salary', 'overtime_pay', 'meal_allowance', 'transport_allowance', 'other_allowance', 'bonus', 'bpjs_deduction', 'tax_deduction', 'loan_deduction', 'other_deduction', 'amount_paid', 'payment_method', 'payment_date', 'notes']
        widgets = {
            'payment_date': DateInput(),
            'notes': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Contoh: bonus panen, lembur, potongan kasbon, atau informasi pembayaran lainnya.',
            }),
        }
        labels = {'notes': 'Keterangan'}

    def __init__(self, *args, period=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.period = period
        qs = Employee.objects.filter(employment_status='active')
        if period:
            used = period.records.exclude(pk=self.instance.pk).values_list('employee_id', flat=True)
            qs = qs.exclude(pk__in=used)
        self.fields['employee'].queryset = qs
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['employee'].widget.attrs['class'] = 'form-select'
        self.fields['payment_method'].widget.attrs['class'] = 'form-select'
