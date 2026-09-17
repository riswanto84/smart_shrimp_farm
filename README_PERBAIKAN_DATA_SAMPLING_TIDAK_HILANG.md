# Perbaikan import sampling ringkas

Masalah terjadi karena template ringkas tidak memiliki kolom ABW, Size, ADG Actual,
SR, Biomassa, dan FCR, tetapi proses update sebelumnya tetap mengisi kolom yang tidak
tersedia tersebut dengan nilai 0.

Perbaikan:
- Template ringkas tidak lagi menimpa kolom yang tidak tersedia dengan 0.
- ABW Today dihitung dari berat sampel / jumlah sampel.
- ADG Actual dihitung dengan `(ABW Today - ABW Last) / 7`.
- Template lebar tetap mempertahankan seluruh angka final dari Excel.
- Data populasi index, pakan kumulatif, tebar, F/D, FR, dan index tetap dibaca dari template ringkas.
