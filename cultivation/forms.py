from django import forms

from .models import CultivationCycle


class CultivationCycleForm(forms.ModelForm):
    """Form siklus yang memastikan nilai tanggal dikonversi menjadi date."""

    class Meta:
        model = CultivationCycle
        fields = [
            "name",
            "start_date",
            "target_duration_days",
            "status",
            "actual_end_date",
            "notes",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "actual_end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["start_date"].input_formats = ["%Y-%m-%d", "%d/%m/%Y"]
        self.fields["actual_end_date"].input_formats = ["%Y-%m-%d", "%d/%m/%Y"]
        self.fields["actual_end_date"].required = False
        self.fields["target_duration_days"].initial = 135

    def clean_target_duration_days(self):
        value = self.cleaned_data.get("target_duration_days") or 135
        if value < 1:
            raise forms.ValidationError("Durasi target minimal 1 hari.")
        return value

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get("start_date")
        actual_end_date = cleaned.get("actual_end_date")
        if start_date and actual_end_date and actual_end_date < start_date:
            self.add_error(
                "actual_end_date",
                "Tanggal selesai aktual tidak boleh lebih awal dari tanggal mulai.",
            )
        return cleaned
