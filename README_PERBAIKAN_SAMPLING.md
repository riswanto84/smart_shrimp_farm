# Perbaikan Form Data Sampling sesuai Data Sampling 2.xlsx

Perubahan utama:

1. Form input mengikuti kolom input Excel: Kolam, Tanggal, DOC, Berat/Jumlah SHRIMP, ADG Target, Pakan Kumulatif, Tebar, F/D, FR, Populasi Index, dan Index.
2. ABW Last dan interval diambil dari sampling sebelumnya pada kolam dan siklus yang sama.
3. Sampling lama/future tidak lagi keliru dipakai ketika mengedit tanggal historis.
4. Pakan harian, pakan kumulatif, DOC, dan tebar mengikuti data sampai tanggal sampling yang dipilih.
5. Populasi Index tetap menjadi input terpisah dan tidak otomatis disamakan dengan Populasi FR.
6. Rumus ABW, Size, ADG, SR, Biomassa, Populasi, dan FCR disamakan dengan Excel.
7. Validasi mencegah DOC, berat, jumlah, FR, dan tebar bernilai nol.
8. Ditambahkan pengujian otomatis di operations/tests_sampling_excel.py.

## Instalasi

```bash
pip install -r requirements.txt
python3 manage.py check
python3 manage.py migrate
python3 manage.py test operations.tests_sampling_excel
python3 manage.py collectstatic --noinput
```
