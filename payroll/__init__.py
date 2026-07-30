# Menjaga kompatibilitas apabila proyek dijalankan pada konfigurasi Django lama.
# Pada Django 4.2, aplikasi utama tetap didaftarkan melalui
# 'payroll.apps.PayrollConfig' di INSTALLED_APPS.
default_app_config = 'payroll.apps.PayrollConfig'
