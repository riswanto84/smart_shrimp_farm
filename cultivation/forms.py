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
            "target_doc",
            "target_size",
            "target_biomass_ton",
            "target_sr_percent",
            "target_fcr",
            "target_adg",
            "target_population",
            "estimated_price_per_kg",
            "target_cost",
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
        numeric_defaults = {
            "target_doc": 120, "target_size": 30, "target_biomass_ton": 25,
            "target_sr_percent": 85, "target_fcr": 1.20, "target_adg": 0.25,
        }
        for name, value in numeric_defaults.items():
            self.fields[name].initial = value
        self.fields["target_population"].required = False
        self.fields["estimated_price_per_kg"].required = False
        self.fields["target_cost"].required = False

    def clean_target_duration_days(self):
        value = self.cleaned_data.get("target_duration_days") or 135
        if value < 1:
            raise forms.ValidationError("Durasi target minimal 1 hari.")
        return value

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get("start_date")
        actual_end_date = cleaned.get("actual_end_date")
        for field_name in ("target_doc", "target_size", "target_biomass_ton", "target_sr_percent", "target_fcr", "target_adg"):
            value = cleaned.get(field_name)
            if value is not None and value <= 0:
                self.add_error(field_name, "Nilai target harus lebih besar dari nol.")
        sr = cleaned.get("target_sr_percent")
        if sr is not None and sr > 100:
            self.add_error("target_sr_percent", "Target SR tidak boleh melebihi 100%.")
        if start_date and actual_end_date and actual_end_date < start_date:
            self.add_error(
                "actual_end_date",
                "Tanggal selesai aktual tidak boleh lebih awal dari tanggal mulai.",
            )
        return cleaned
