"""
Paket konfigurasi proyek RANAH.

Berkas ini dieksekusi paling awal. Di sini kita mengaktifkan PyMySQL agar
Django menganggapnya sebagai driver "MySQLdb". Dengan cara ini kita tidak
perlu memasang mysqlclient (yang butuh compiler C).

Jika PyMySQL tidak terpasang (misalnya Anda memakai mysqlclient, atau
sedang uji cepat dengan SQLite), blok try/except akan melewatinya.
"""

try:
    import pymysql

    # Django memeriksa versi driver; kita samarkan versi PyMySQL agar lolos.
    pymysql.version_info = (2, 2, 1, "final", 0)
    pymysql.install_as_MySQLdb()
except ImportError:  # pragma: no cover
    pass
