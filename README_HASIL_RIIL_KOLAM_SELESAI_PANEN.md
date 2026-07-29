# Hasil Riil Kolam Selesai Panen pada Dashboard

Perbaikan pada **Dashboard > Ringkasan Kolam**:

- Kolam berstatus selesai panen tetap tidak dimasukkan ke estimasi produksi aktif.
- Kolom **Estimasi DOC 120** untuk kolam selesai panen tidak lagi menampilkan `0,00 ton`.
- Angka tersebut diganti dengan akumulasi hasil panen riil kolam dari seluruh pencatatan panen parsial dan panen total pada siklus yang dipilih.
- Keterangan yang tampil: **Hasil riil total yang telah dipanen**.
- Kolam aktif tetap menampilkan estimasi biomassa DOC 120 seperti sebelumnya.

Tidak ada perubahan model atau migration database.
