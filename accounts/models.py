"""
Model aplikasi `accounts`.

Berisi dua tabel:
  * Opd  - daftar OPD/instansi mitra (sumber data PDRB).
  * User - pengguna aplikasi. Memperluas User bawaan Django dengan kolom
           `peran` (role) dan `opd`, sehingga hak akses bisa ditentukan
           sesuai tabel "Pengguna dan Hak Akses" pada rancangan RANAH.

Catatan: konstanta peran memakai string biasa (bukan Enum) agar mudah
dibandingkan di mana saja, misalnya:  user.peran == PERAN_TEKNIS
"""
from django.contrib.auth.models import AbstractUser
from django.db import models

# --- Konstanta peran ------------------------------------------------------
PERAN_TEKNIS = "teknis"    # Tim Teknis
PERAN_PIC = "pic"          # PIC OPD/instansi
PERAN_ADMIN = "admin"      # Tim Administrasi
PERAN_TI = "ti"            # Tim TI
PERAN_HUMAS = "humas"      # Humas
PERAN_LEADER = "leader"    # Project Leader
PERAN_MENTOR = "mentor"    # Mentor / Pimpinan

PILIHAN_PERAN = [
    (PERAN_TEKNIS, "Tim Teknis"),
    (PERAN_PIC, "PIC OPD/Instansi"),
    (PERAN_ADMIN, "Tim Administrasi"),
    (PERAN_TI, "Tim TI"),
    (PERAN_HUMAS, "Humas"),
    (PERAN_LEADER, "Project Leader"),
    (PERAN_MENTOR, "Mentor/Pimpinan"),
]


class Opd(models.Model):
    """OPD / instansi mitra penyedia data."""

    nama = models.CharField("Nama OPD/instansi", max_length=200, unique=True)
    singkatan = models.CharField("Singkatan", max_length=30)
    sektor = models.CharField("Sektor utama", max_length=100, blank=True)

    class Meta:
        ordering = ["nama"]
        verbose_name = "OPD/Instansi"
        verbose_name_plural = "OPD/Instansi"

    def __str__(self):
        return self.singkatan or self.nama


class User(AbstractUser):
    """Pengguna RANAH = User Django + peran + OPD."""

    peran = models.CharField(
        "Peran", max_length=10, choices=PILIHAN_PERAN, default=PERAN_MENTOR,
        help_text="Menentukan hak akses pada setiap komponen.",
    )
    opd = models.ForeignKey(
        Opd, verbose_name="OPD/Instansi", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="pengguna",
        help_text="Wajib diisi untuk peran PIC OPD/Instansi.",
    )
    telepon = models.CharField("Telepon", max_length=30, blank=True)

    class Meta:
        verbose_name = "Pengguna"
        verbose_name_plural = "Pengguna"

    @property
    def nama_tampil(self) -> str:
        """Nama lengkap bila ada, jika tidak pakai username."""
        return self.get_full_name() or self.username

    @property
    def label_peran(self) -> str:
        """Teks peran yang mudah dibaca (mis. 'Tim Teknis')."""
        return self.get_peran_display()

    def __str__(self):
        return self.nama_tampil
