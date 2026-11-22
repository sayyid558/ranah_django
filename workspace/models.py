"""
Model (tabel database) untuk 6 komponen RANAH.

Peta komponen -> model:
  1. Matriks Kebutuhan Data dan Jadwal  -> ButirData
  2. Log Verifikasi dan Permintaan Ulang -> LogVerifikasi
  3. Matriks Tindak Lanjut Forum         -> TindakLanjut
  4. Kalender Koordinasi dan Pengingat   -> Agenda
  5. Pustaka Dokumen                     -> Dokumen
  6. Rekap Indikator                     -> TargetIndikator (nilai realisasi
     dihitung otomatis dari model 1-3, lihat workspace/indikator.py)
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# Fungsi & konstanta bantu
# ---------------------------------------------------------------------------
def tahun_default() -> int:
    """Tahun berjalan - nilai awal kolom `tahun`."""
    return timezone.localdate().year


def triwulan_sekarang() -> int:
    """Triwulan berjalan (1-4) berdasarkan bulan hari ini."""
    return (timezone.localdate().month - 1) // 3 + 1


PILIHAN_TRIWULAN = [(1, "Triwulan I"), (2, "Triwulan II"), (3, "Triwulan III"), (4, "Triwulan IV")]

# Status butir data (komponen 1)
STATUS_BELUM = "belum"
STATUS_DITERIMA = "diterima"
STATUS_TERVERIFIKASI = "terverifikasi"
STATUS_REVISI = "revisi"
PILIHAN_STATUS_DATA = [
    (STATUS_BELUM, "Belum diterima"),
    (STATUS_DITERIMA, "Diterima"),
    (STATUS_TERVERIFIKASI, "Terverifikasi"),
    (STATUS_REVISI, "Perlu revisi"),
]

# Status tindak lanjut (komponen 3)
TL_BARU = "baru"
TL_PROSES = "proses"
TL_SELESAI = "selesai"
PILIHAN_STATUS_TL = [(TL_BARU, "Baru"), (TL_PROSES, "Dalam proses"), (TL_SELESAI, "Selesai")]

# Jenis agenda (komponen 4)
AG_FORUM = "forum"
AG_BATAS = "batas"
AG_LAIN = "lain"
PILIHAN_JENIS_AGENDA = [
    (AG_FORUM, "Forum Data dan Fenomena Ekonomi"),
    (AG_BATAS, "Batas waktu data"),
    (AG_LAIN, "Kegiatan koordinasi lain"),
]

# Kategori dokumen (komponen 5)
PILIHAN_KATEGORI_DOKUMEN = [
    ("sop", "SOP"),
    ("format", "Format data/fenomena"),
    ("panduan", "Panduan penggunaan"),
    ("undangan", "Undangan"),
    ("hadir", "Daftar hadir"),
    ("notulen", "Notulen"),
    ("bahan_forum", "Bahan forum"),
    ("bahan_analisis", "Bahan analisis"),
]

# Kode indikator (komponen 6)
PILIHAN_KODE_INDIKATOR = [(k, k) for k in ("H1", "H2", "H3", "P1", "P2", "P3")]


# ===========================================================================
# KOMPONEN 1 - Matriks Kebutuhan Data dan Jadwal
# ===========================================================================
class ButirData(models.Model):
    """Satu baris = satu butir data yang diminta dari sebuah OPD/instansi."""

    kode = models.CharField("Kode butir", max_length=30, unique=True)
    jenis_data = models.CharField("Jenis data", max_length=200)
    sektor = models.CharField("Sektor", max_length=100)
    opd = models.ForeignKey(
        "accounts.Opd", verbose_name="OPD/Instansi", on_delete=models.PROTECT,
        related_name="butir_data",
    )
    pic = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="PIC", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="butir_data_pic",
    )
    tahun = models.PositiveSmallIntegerField("Tahun", default=tahun_default)
    triwulan = models.PositiveSmallIntegerField("Triwulan", choices=PILIHAN_TRIWULAN, default=triwulan_sekarang)
    periode_referensi = models.CharField("Periode referensi", max_length=100, help_text="Mis. Januari-Maret 2026")
    cakupan = models.CharField("Cakupan", max_length=150, help_text="Mis. Seluruh kabupaten/kota")
    satuan = models.CharField("Satuan", max_length=50, help_text="Mis. Ton, Juta Rupiah")
    batas_waktu = models.DateField("Batas waktu penerimaan")
    tanggal_diterima = models.DateField("Tanggal diterima", null=True, blank=True)
    status = models.CharField("Status", max_length=15, choices=PILIHAN_STATUS_DATA, default=STATUS_BELUM)
    catatan = models.TextField("Catatan", blank=True)
    dibuat = models.DateTimeField(auto_now_add=True)
    diubah = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["tahun", "triwulan", "batas_waktu", "kode"]
        verbose_name = "Butir data"
        verbose_name_plural = "Butir data"

    def __str__(self):
        return f"{self.kode} - {self.jenis_data}"

    # --- Properti turunan (tidak disimpan di database) --------------------
    @property
    def tepat_waktu(self) -> bool:
        """True bila sudah diterima pada/ sebelum batas waktu."""
        return self.tanggal_diterima is not None and self.tanggal_diterima <= self.batas_waktu

    @property
    def terlambat(self) -> bool:
        """True bila diterima setelah batas, atau belum diterima padahal batas lewat."""
        if self.tanggal_diterima:
            return self.tanggal_diterima > self.batas_waktu
        return timezone.localdate() > self.batas_waktu

    @property
    def jumlah_permintaan_ulang(self) -> int:
        """Berapa kali butir ini diminta ulang (dari komponen 2)."""
        return self.log_verifikasi.filter(perlu_permintaan_ulang=True).count()

    def save(self, *args, **kwargs):
        # Bila tanggal diterima diisi tetapi status masih "belum", naikkan ke "diterima".
        if self.tanggal_diterima and self.status == STATUS_BELUM:
            self.status = STATUS_DITERIMA
        super().save(*args, **kwargs)


# ===========================================================================
# KOMPONEN 2 - Log Verifikasi dan Permintaan Ulang
# ===========================================================================
class LogVerifikasi(models.Model):
    """Hasil pemeriksaan sebuah butir data (kelengkapan, periode, cakupan, satuan)."""

    butir = models.ForeignKey(ButirData, verbose_name="Butir data", on_delete=models.CASCADE, related_name="log_verifikasi")
    tanggal = models.DateField("Tanggal verifikasi", default=timezone.localdate)
    lengkap = models.BooleanField("Data lengkap", default=True)
    periode_sesuai = models.BooleanField("Periode sesuai", default=True)
    cakupan_sesuai = models.BooleanField("Cakupan sesuai", default=True)
    satuan_sesuai = models.BooleanField("Satuan sesuai", default=True)
    catatan_klarifikasi = models.TextField("Catatan klarifikasi", blank=True)
    perlu_permintaan_ulang = models.BooleanField("Perlu permintaan ulang", default=False, editable=False)
    jawaban_klarifikasi = models.TextField("Jawaban klarifikasi (PIC)", blank=True)
    tanggal_jawaban = models.DateTimeField("Waktu dijawab", null=True, blank=True, editable=False)
    diverifikasi_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Diverifikasi oleh", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="log_verifikasi_dibuat", editable=False,
    )
    dibuat = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-tanggal", "-id"]
        verbose_name = "Log verifikasi"
        verbose_name_plural = "Log verifikasi"

    def __str__(self):
        return f"Verifikasi {self.butir.kode} ({self.tanggal})"

    @property
    def semua_sesuai(self) -> bool:
        return all([self.lengkap, self.periode_sesuai, self.cakupan_sesuai, self.satuan_sesuai])

    # Dua pasang "properti + get_..._display" ini meniru pola field `choices`
    # sehingga tabel generik dapat menampilkannya sebagai lencana berwarna.
    @property
    def hasil(self) -> str:
        return STATUS_TERVERIFIKASI if self.semua_sesuai else STATUS_REVISI

    def get_hasil_display(self) -> str:
        return "Lengkap & sesuai" if self.semua_sesuai else "Perlu permintaan ulang"

    @property
    def status_klarifikasi(self) -> str:
        if not self.catatan_klarifikasi:
            return "tidak_ada"
        return "dijawab" if self.jawaban_klarifikasi else "menunggu"

    def get_status_klarifikasi_display(self) -> str:
        return {"tidak_ada": "Tidak ada", "menunggu": "Menunggu jawaban", "dijawab": "Sudah dijawab"}[self.status_klarifikasi]

    def save(self, *args, **kwargs):
        # 1) Permintaan ulang otomatis bila ada pemeriksaan yang gagal.
        self.perlu_permintaan_ulang = not self.semua_sesuai
        # 2) Catat waktu saat jawaban pertama kali diisi.
        if self.jawaban_klarifikasi and not self.tanggal_jawaban:
            self.tanggal_jawaban = timezone.now()
        super().save(*args, **kwargs)
        # 3) Bila ini log terbaru, sinkronkan status butir data (komponen 1).
        terbaru = self.butir.log_verifikasi.order_by("-tanggal", "-id").first()
        if terbaru is not None and terbaru.pk == self.pk:
            self.butir.status = STATUS_TERVERIFIKASI if self.semua_sesuai else STATUS_REVISI
            self.butir.save(update_fields=["status", "diubah"])


# ===========================================================================
# KOMPONEN 4 - Kalender Koordinasi dan Pengingat
# (didefinisikan sebelum TindakLanjut karena TindakLanjut merujuk Agenda)
# ===========================================================================
class Agenda(models.Model):
    """Jadwal forum, batas waktu data, atau kegiatan koordinasi lain."""

    judul = models.CharField("Judul", max_length=200)
    jenis = models.CharField("Jenis", max_length=10, choices=PILIHAN_JENIS_AGENDA, default=AG_FORUM)
    tanggal = models.DateField("Tanggal")
    jam = models.TimeField("Jam mulai", null=True, blank=True)
    lokasi = models.CharField("Lokasi / tautan rapat", max_length=200, blank=True)
    deskripsi = models.TextField("Deskripsi", blank=True)
    pengingat_hari = models.PositiveSmallIntegerField(
        "Pengingat (hari sebelumnya)", default=3,
        help_text="Email pengingat otomatis dikirim ke seluruh PIC sekian hari sebelum acara.",
    )
    dibuat_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="agenda_dibuat", editable=False,
    )

    class Meta:
        ordering = ["tanggal", "jam"]
        verbose_name = "Agenda"
        verbose_name_plural = "Agenda"

    def __str__(self):
        return f"{self.judul} ({self.tanggal})"


# ===========================================================================
# KOMPONEN 3 - Matriks Tindak Lanjut Forum
# ===========================================================================
class TindakLanjut(models.Model):
    """Isu/temuan dari forum beserta tindak lanjut, penanggung jawab, dan status."""

    isu = models.CharField("Isu / temuan", max_length=300)
    tindak_lanjut = models.TextField("Tindak lanjut")
    agenda = models.ForeignKey(
        Agenda, verbose_name="Forum asal", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="tindak_lanjut",
    )
    opd = models.ForeignKey(
        "accounts.Opd", verbose_name="OPD/Instansi", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="tindak_lanjut",
    )
    penanggung_jawab = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="Penanggung jawab", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="tindak_lanjut_pj",
    )
    tahun = models.PositiveSmallIntegerField("Tahun", default=tahun_default)
    triwulan = models.PositiveSmallIntegerField("Triwulan", choices=PILIHAN_TRIWULAN, default=triwulan_sekarang)
    batas_waktu = models.DateField("Batas waktu")
    status = models.CharField("Status", max_length=10, choices=PILIHAN_STATUS_TL, default=TL_BARU)
    tanggal_selesai = models.DateField("Tanggal selesai", null=True, blank=True, editable=False)
    catatan = models.TextField("Catatan perkembangan", blank=True)
    dibuat = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["status", "batas_waktu"]
        verbose_name = "Tindak lanjut"
        verbose_name_plural = "Tindak lanjut"

    def __str__(self):
        return self.isu

    @property
    def terlambat(self) -> bool:
        if self.status == TL_SELESAI and self.tanggal_selesai:
            return self.tanggal_selesai > self.batas_waktu
        return self.status != TL_SELESAI and timezone.localdate() > self.batas_waktu

    def save(self, *args, **kwargs):
        # Tanggal selesai otomatis terisi/terhapus mengikuti status.
        if self.status == TL_SELESAI and not self.tanggal_selesai:
            self.tanggal_selesai = timezone.localdate()
        elif self.status != TL_SELESAI:
            self.tanggal_selesai = None
        super().save(*args, **kwargs)


# ===========================================================================
# KOMPONEN 5 - Pustaka Dokumen
# ===========================================================================
def validasi_ukuran(berkas):
    """Menolak berkas yang lebih besar dari UKURAN_MAKS_UNGGAHAN_MB."""
    batas = settings.UKURAN_MAKS_UNGGAHAN_MB * 1024 * 1024
    if berkas.size > batas:
        raise ValidationError(f"Ukuran berkas maksimal {settings.UKURAN_MAKS_UNGGAHAN_MB} MB.")


class Dokumen(models.Model):
    """Berkas SOP, format, panduan, notulen, bahan forum, dan sebagainya."""

    judul = models.CharField("Judul dokumen", max_length=200)
    kategori = models.CharField("Kategori", max_length=20, choices=PILIHAN_KATEGORI_DOKUMEN)
    berkas = models.FileField(
        "Berkas", upload_to="pustaka/%Y/%m/",
        validators=[
            FileExtensionValidator(["pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "csv", "txt", "png", "jpg", "jpeg", "zip"]),
            validasi_ukuran,
        ],
    )
    deskripsi = models.TextField("Deskripsi", blank=True)
    diunggah_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="dokumen", editable=False,
    )
    dibuat = models.DateTimeField("Diunggah pada", auto_now_add=True)

    class Meta:
        ordering = ["-dibuat"]
        verbose_name = "Dokumen"
        verbose_name_plural = "Dokumen"

    def __str__(self):
        return self.judul

    @property
    def ekstensi(self) -> str:
        return self.berkas.name.rsplit(".", 1)[-1].upper() if "." in self.berkas.name else "FILE"


# ===========================================================================
# KOMPONEN 6 - Rekap Indikator (target; realisasi dihitung otomatis)
# ===========================================================================
class TargetIndikator(models.Model):
    """Target capaian indikator per triwulan. Realisasi dihitung di indikator.py."""

    kode = models.CharField("Indikator", max_length=2, choices=PILIHAN_KODE_INDIKATOR)
    tahun = models.PositiveSmallIntegerField("Tahun")
    triwulan = models.PositiveSmallIntegerField("Triwulan", choices=PILIHAN_TRIWULAN)
    target = models.DecimalField("Target", max_digits=8, decimal_places=2)

    class Meta:
        unique_together = [("kode", "tahun", "triwulan")]
        ordering = ["tahun", "triwulan", "kode"]
        verbose_name = "Target indikator"
        verbose_name_plural = "Target indikator"

    def __str__(self):
        return f"{self.kode} TW{self.triwulan}/{self.tahun}: {self.target}"

# ===========================================================================
# KOMPONEN 7 - Input Data (input data dari OPD terkait)
# ===========================================================================
class OPD(models.Model):
    nama_opd = models.CharField(max_length=100)

    def __str__(self):
        return self.nama_opd

class JenisData(models.Model):
    opd = models.ForeignKey(OPD, on_delete=models.CASCADE, related_name='jenis_data')
    nama_jenis_data = models.CharField(max_length=150)

    def __str__(self):
        return self.nama_jenis_data

class PencapaianData(models.Model):
    opd = models.CharField(max_length=50)
    jenis_data = models.CharField(max_length=100) # Ubah jadi CharField biasa
    tahun = models.IntegerField()
    triwulan = models.CharField(max_length=10, choices=[('TW I', 'Triwulan I'), ('TW II', 'Triwulan II'), ('TW III', 'Triwulan III'), ('TW IV', 'Triwulan IV')])
    nilai = models.FloatField()