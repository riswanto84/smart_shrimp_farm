# Perbaikan Grafik Laporan Keuangan Periodik

Perbaikan ini mengatasi grafik omzet/pengeluaran/laba dan komposisi biaya yang kosong walaupun kartu ringkasan memiliki nilai.

Penyebab utama adalah serialisasi JSON dua kali: `json.dumps()` di view kemudian kembali diserialisasi oleh template filter `json_script`. Akibatnya JavaScript menerima string, bukan object/dataset numerik.

Perubahan:
- context chart sekarang mengirim object/list Python langsung ke `json_script`;
- JavaScript tetap kompatibel dengan format lama yang terserialisasi dua kali;
- seluruh dataset dinormalisasi menjadi angka valid sebelum diberikan ke Chart.js;
- formatter rupiah hanya digunakan untuk tooltip dan sumbu, bukan pada data mentah;
- error pemuatan Chart.js dan parsing data dicatat di browser console.

Tidak ada perubahan model atau migration database.
