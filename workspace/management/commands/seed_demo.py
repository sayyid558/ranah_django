"""
Perintah:  python manage.py seed_demo

Mengisi database dengan DATA CONTOH agar aplikasi langsung bisa dicoba:
OPD, akun untuk setiap peran, butir data, log verifikasi, tindak lanjut,
agenda, dokumen, dan target indikator.

Aman dijalankan berulang: bila akun/butir sudah ada, tidak digandakan.
Gunakan  --reset  untuk menghapus data contoh lama terlebih dulu.
"""
import random
from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import (
    Opd, User, PERAN_ADMIN, PERAN_HUMAS, PERAN_LEADER, PERAN_MENTOR,
    PERAN_PIC, PERAN_TEKNIS, PERAN_TI,
)
from workspace.models import (
    Agenda, ButirData, Dokumen, LogVerifikasi, TargetIndikator, TindakLanjut,
    STATUS_BELUM, STATUS_DITERIMA, TL_BARU, TL_PROSES, TL_SELESAI,
    AG_BATAS, AG_FORUM, AG_LAIN,
)

KATA_SANDI = "ranah12345"

OPD_CONTOH = [
    ("Dinas Pertanian dan Ketahanan Pangan", "DISTAN", "Pertanian"),
    ("Dinas Perindustrian dan Perdagangan", "DISPERINDAG", "Industri & Perdagangan"),
    ("Dinas Pekerjaan Umum dan Penataan Ruang", "DPUPR", "Konstruksi"),
    ("Dinas Energi dan Sumber Daya Mineral", "DESDM", "Pertambangan"),
    ("Dinas Perhubungan", "DISHUB", "Transportasi"),
]

# (kode, jenis data, sektor, indeks OPD)
BUTIR_CONTOH = [
    ("PRT-01", "Luas panen dan produksi padi", "Pertanian", 0),
    ("PRT-02", "Produksi tanaman hortikultura", "Pertanian", 0),
    ("PRT-03", "Populasi dan produksi peternakan", "Pertanian", 0),
    ("IND-01", "Indeks produksi industri besar sedang", "Industri", 1),
    ("IND-02", "Nilai ekspor-impor daerah", "Perdagangan", 1),
    ("KON-01", "Nilai proyek konstruksi pemerintah", "Konstruksi", 2),
    ("KON-02", "Realisasi belanja modal infrastruktur", "Konstruksi", 2),
    ("TAM-01", "Produksi komoditas pertambangan", "Pertambangan", 3),
    ("TAM-02", "Realisasi penerimaan royalti", "Pertambangan", 3),
    ("TRN-01", "Jumlah penumpang angkutan darat", "Transportasi", 4),
    ("TRN-02", "Arus barang pelabuhan", "Transportasi", 4),
    ("TRN-03", "Jumlah armada angkutan umum", "Transportasi", 4),
]

NAMA_BULAN_TW = {1: "Januari-Maret", 2: "April-Juni", 3: "Juli-September", 4: "Oktober-Desember"}


class Command(BaseCommand):
    help = "Mengisi data contoh RANAH (OPD, akun tiap peran, butir data, dll)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Hapus data contoh lama sebelum mengisi.")

    def handle(self, *args, **opsi):
        random.seed(42)  # hasil acak selalu sama agar mudah diajarkan
        if opsi["reset"]:
            self._reset()
        opd = self._buat_opd()
        akun = self._buat_akun(opd)
        butir = self._buat_butir(opd, akun)
        self._buat_log(butir, akun["teknis"])
        agenda = self._buat_agenda(akun["teknis"])
        self._buat_tindak_lanjut(opd, akun, agenda)
        self._buat_dokumen(akun)
        self._buat_target()
        self._cetak_ringkasan()

    # --------------------------------------------------------------------
    def _reset(self):
        for model in (LogVerifikasi, TindakLanjut, ButirData, Agenda, Dokumen, TargetIndikator):
            model.objects.all().delete()
        self.stdout.write("Data contoh lama dihapus.")

    def _buat_opd(self):
        hasil = []
        for nama, singkatan, sektor in OPD_CONTOH:
            obj, _ = Opd.objects.get_or_create(nama=nama, defaults={"singkatan": singkatan, "sektor": sektor})
            hasil.append(obj)
        return hasil

    def _akun(self, username, peran, depan, belakang, opd=None, super_user=False):
        user, baru = User.objects.get_or_create(username=username, defaults={
            "peran": peran, "first_name": depan, "last_name": belakang, "opd": opd,
            "email": f"{username}@contoh.go.id", "is_staff": super_user, "is_superuser": super_user,
        })
        if baru:
            user.set_password(KATA_SANDI)   # set_password menyimpan hash, bukan teks asli
            user.save()
        return user

    def _buat_akun(self, opd):
        akun = {
            "admin": self._akun("admin", PERAN_TEKNIS, "Admin", "Sistem", super_user=True),
            "teknis": self._akun("teknis", PERAN_TEKNIS, "Tim", "Teknis"),
            "leader": self._akun("leader", PERAN_LEADER, "Project", "Leader"),
            "mentor": self._akun("mentor", PERAN_MENTOR, "Mentor", "Pimpinan"),
            "admintim": self._akun("admintim", PERAN_ADMIN, "Tim", "Administrasi"),
            "ti": self._akun("ti", PERAN_TI, "Tim", "TI"),
            "humas": self._akun("humas", PERAN_HUMAS, "Tim", "Humas"),
        }
        for i, o in enumerate(opd, start=1):
            akun[f"pic{i}"] = self._akun(f"pic{i}", PERAN_PIC, "PIC", o.singkatan, opd=o)
        return akun

    def _buat_butir(self, opd, akun):
        hari = timezone.localdate()
        tahun = hari.year
        tw_ini = (hari.month - 1) // 3 + 1
        hasil = []
        for nomor, (kode, jenis, sektor, idx) in enumerate(BUTIR_CONTOH):
            tw = tw_ini if nomor % 3 else max(1, tw_ini - 1)   # sebagian di triwulan sebelumnya
            batas = hari + timedelta(days=random.randint(-20, 25))
            # Variasi status: sebagian sudah diterima (tepat waktu/terlambat), sebagian belum.
            diterima, status = None, STATUS_BELUM
            if random.random() < 0.65:
                diterima = batas + timedelta(days=random.randint(-6, 5))
                if diterima > hari:
                    diterima = hari
                status = STATUS_DITERIMA
            obj, _ = ButirData.objects.get_or_create(kode=kode, defaults={
                "jenis_data": jenis, "sektor": sektor, "opd": opd[idx], "pic": akun[f"pic{idx + 1}"],
                "tahun": tahun, "triwulan": tw, "periode_referensi": f"{NAMA_BULAN_TW[tw]} {tahun}",
                "cakupan": "Seluruh kabupaten/kota", "satuan": random.choice(["Ton", "Juta Rupiah", "Orang", "Unit"]),
                "batas_waktu": batas, "tanggal_diterima": diterima, "status": status,
            })
            hasil.append(obj)
        return hasil

    def _buat_log(self, butir, teknis):
        if LogVerifikasi.objects.exists():
            return
        for obj in butir:
            if obj.status == STATUS_BELUM:
                continue
            ok = random.random() < 0.6
            log = LogVerifikasi(
                butir=obj, tanggal=timezone.localdate(), diverifikasi_oleh=teknis,
                lengkap=ok or random.random() < 0.5, periode_sesuai=True,
                cakupan_sesuai=ok or random.random() < 0.5, satuan_sesuai=ok or random.random() < 0.7,
            )
            if not log.semua_sesuai:
                log.catatan_klarifikasi = "Mohon lengkapi data dan periksa kembali cakupan serta satuan sesuai format."
                if random.random() < 0.4:
                    log.jawaban_klarifikasi = "Sudah kami perbaiki, berkas revisi dikirim melalui email."
            log.save()

    def _buat_agenda(self, teknis):
        if Agenda.objects.exists():
            return list(Agenda.objects.all())
        hari = timezone.localdate()
        data = [
            ("Forum Data dan Fenomena Ekonomi Triwulanan", AG_FORUM, 9, "Aula Kantor, Lantai 2"),
            ("Batas pengiriman data triwulan berjalan", AG_BATAS, 14, ""),
            ("Rapat koordinasi PIC OPD/instansi", AG_LAIN, 3, "Zoom Meeting"),
            ("Pembahasan hasil verifikasi data", AG_LAIN, 20, "Ruang Rapat Utama"),
        ]
        return [
            Agenda.objects.create(judul=j, jenis=k, tanggal=hari + timedelta(days=d), lokasi=lok, dibuat_oleh=teknis)
            for j, k, d, lok in data
        ]

    def _buat_tindak_lanjut(self, opd, akun, agenda):
        if TindakLanjut.objects.exists():
            return
        hari = timezone.localdate()
        tw = (hari.month - 1) // 3 + 1
        data = [
            ("Data produksi padi belum memakai satuan ubinan terbaru", "Sosialisasi format data baru kepada PIC", 0, TL_PROSES, 10),
            ("Keterlambatan data realisasi belanja modal", "Menyepakati jadwal pengiriman data bulanan", 2, TL_BARU, 14),
            ("Cakupan data ekspor belum mencakup UMKM", "Penambahan sumber data dari asosiasi eksportir", 1, TL_SELESAI, -3),
            ("Perbedaan definisi produksi tambang", "Penyelarasan definisi dengan instansi pusat", 3, TL_PROSES, 7),
            ("Data armada angkutan umum belum diperbarui", "Pembaruan data melalui sistem perizinan", 4, TL_BARU, -2),
        ]
        for isu, aksi, idx, status, hari_batas in data:
            TindakLanjut.objects.create(
                isu=isu, tindak_lanjut=aksi, opd=opd[idx], penanggung_jawab=akun[f"pic{idx + 1}"],
                agenda=agenda[0] if agenda else None, tahun=hari.year, triwulan=tw,
                batas_waktu=hari + timedelta(days=hari_batas), status=status,
            )

    def _buat_dokumen(self, akun):
        if Dokumen.objects.exists():
            return
        contoh = [
            ("SOP Pengumpulan dan Verifikasi Data PDRB", "sop", "sop-pengumpulan-data.txt", "Alur kerja pengumpulan data dari OPD/instansi."),
            ("Format Isian Data Triwulanan", "format", "format-data.txt", "Format baku pengisian butir data."),
            ("Panduan Penggunaan Ruang Kerja RANAH", "panduan", "panduan-ranah.txt", "Panduan singkat untuk seluruh pengguna."),
            ("Notulen Forum Data dan Fenomena Ekonomi", "notulen", "notulen-forum.txt", "Ringkasan hasil pembahasan forum."),
        ]
        for judul, kat, nama, desk in contoh:
            dok = Dokumen(judul=judul, kategori=kat, deskripsi=desk, diunggah_oleh=akun["admintim"])
            dok.berkas.save(nama, ContentFile(f"{judul}\n\n(Dokumen contoh RANAH)\n".encode("utf-8")), save=False)
            dok.save()

    def _buat_target(self):
        tahun = timezone.localdate().year
        target = {"H1": 90, "H2": 85, "H3": 80, "P1": 1.0, "P2": 2, "P3": 75}
        for kode, nilai in target.items():
            for tw in (1, 2, 3, 4):
                TargetIndikator.objects.get_or_create(kode=kode, tahun=tahun, triwulan=tw, defaults={"target": nilai})

    def _cetak_ringkasan(self):
        self.stdout.write(self.style.SUCCESS("\nData contoh RANAH siap. Akun demo (kata sandi semuanya: %s):" % KATA_SANDI))
        for u in User.objects.order_by("id"):
            self.stdout.write(f"  {u.username:<10} {u.get_peran_display()}")
