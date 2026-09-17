# Form Data Sampling — Mapping Data Sampling 2.xlsx

Form sampling telah disesuaikan dengan kolom dan rumus lembar Excel.

## Input lapangan

- Kolam
- Tanggal
- DOC
- SHRIMP Berat (gram)
- SHRIMP Jumlah (ekor)
- ADG Weekly Target
- Pakan Kumulatif (kg)
- Tebar (ekor)
- F/D / Pakan Harian (kg)
- FR (%)
- Populasi Index (ekor)
- Index

## Hasil otomatis

- ABW Last: sampling sebelumnya pada kolam dan siklus yang sama
- ABW Today = Berat / Jumlah
- ABW Target = ABW Last + (ADG Target × interval)
- Size Today = 1000 / ABW Today
- Target Size = 1000 / ABW Target
- ADG Actual = (ABW Today − ABW Last) / interval
- ADG Accum = ABW Today / DOC
- Biomassa FR = F/D / FR × 100
- Populasi FR = Biomassa FR × Size Today
- SR FR = Populasi FR / Tebar × 100
- Biomassa Index = Populasi Index / Size Today
- SR Index = Populasi Index / Tebar × 100
- FCR = Pakan Kumulatif / Biomassa FR

Perhitungan sebelumnya, tebar, pakan harian, dan pakan kumulatif dibatasi pada siklus aktif serta tanggal sampling yang dipilih.
