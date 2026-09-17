from decimal import Decimal, InvalidOperation
from django import forms
from .models import Employee, PayrollPeriod, PayrollRecord




class IndonesianMoneyField(forms.DecimalField):
    """Input nominal dengan tampilan pemisah ribuan Indonesia."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('min_value', Decimal('0'))
        kwargs.setdefault('decimal_places', 2)
        kwargs.setdefault('max_digits', 16)
        kwargs.setdefault('widget', forms.TextInput(attrs={
            'inputmode': 'numeric',
            'autocomplete': 'off',
            'class': 'form-control money-input',
            'placeholder': '0',
        }))
        super().__init__(*args, **kwargs)

    def prepare_value(self, value):
        if value in (None, ''):
            return '0'
        try:
            number = Decimal(str(value))
            return f"{int(number):,}".replace(',', '.')
        except (InvalidOperation, ValueError, TypeError):
            return value

    def to_python(self, value):
        if isinstance(value, str):
            value = value.strip().replace('Rp', '').replace(' ', '')
            # Form ini khusus nominal rupiah bulat; titik/koma pada UI dianggap pemisah ribuan.
            value = value.replace('.', '').replace(',', '') or '0'
        return super().to_python(value)


class EmployeeChoiceField(forms.ModelChoiceField):
    """Pilihan karyawan dengan label informatif untuk pencarian."""
    def label_from_instance(self, obj):
        position = f" · {obj.position}" if obj.position else ""
        return f"{obj.employee_code} - {obj.name}{position}"


class DateInput(forms.DateInput):
    input_type = 'date'


class EmployeeForm(forms.ModelForm):
    base_salary = IndonesianMoneyField(label='Gaji Pokok')
    daily_rate = IndonesianMoneyField(label='Upah Harian')
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
    employee = EmployeeChoiceField(
        queryset=Employee.objects.none(),
        label='Karyawan',
        empty_label='Pilih karyawan',
    )

    class Meta:
        model = PayrollRecord
        fields = ['employee', 'work_days', 'base_salary', 'overtime_pay', 'meal_allowance', 'transport_allowance', 'other_allowance', 'bonus', 'bpjs_deduction', 'tax_deduction', 'loan_deduction', 'other_deduction', 'amount_paid', 'payment_method', 'payment_date', 'notes', 'catatan']
        widgets = {
            'payment_date': DateInput(),
            'notes': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Contoh: bonus panen, lembur, potongan kasbon, atau informasi pembayaran lainnya.',
            }),
            'catatan': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Masukkan catatan tambahan untuk data gaji karyawan.',
            }),
        }
        labels = {'notes': 'Keterangan', 'catatan': 'Catatan'}

    def __init__(self, *args, period=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.period = period
        qs = Employee.objects.filter(employment_status='active')
        if period:
            used = period.records.exclude(pk=self.instance.pk).values_list('employee_id', flat=True)
            qs = qs.exclude(pk__in=used)
        self.fields['employee'].queryset = qs.order_by('name', 'employee_code')
        self.fields['employee'].label = 'Karyawan'
        self.fields['employee'].widget.attrs.update({
            'class': 'form-select employee-search-source',
            'data-searchable': 'true',
            'autocomplete': 'off',
        })
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
        self.fields['payment_method'].widget.attrs['class'] = 'form-select'
