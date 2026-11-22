"""
View (logika halaman) RANAH.

Struktur berkas (dibaca dari atas ke bawah):

  A. Kelas dasar generik  -> KomponenMixin, DaftarView, TambahView, UbahView, HapusView
  B. Dashboard
  C. Komponen 1  Matriks Kebutuhan Data dan Jadwal
  D. Komponen 2  Log Verifikasi dan Permintaan Ulang
  E. Komponen 3  Matriks Tindak Lanjut Forum
  F. Komponen 4  Kalender Koordinasi dan Pengingat
  G. Komponen 5  Pustaka Dokumen
  H. Komponen 6  Rekap Indikator

Ide utamanya: halaman daftar/tambah/ubah/hapus untuk komponen 1-3 dibuat
dari satu kelas dasar yang sama. Tiap komponen cukup mengisi atribut
(model, kolom tabel, form) sehingga kodenya pendek dan konsisten.
"""
import calendar
import os
import openpyxl
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from openpyxl.styles import Alignment, Font, PatternFill
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import FileResponse, Http404, JsonResponse,HttpResponse
from django.shortcuts import get_object_or_404, redirect, render, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.text import Truncator
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, TemplateView, UpdateView

from accounts.models import PERAN_PIC
from accounts.permissions import batasi_opd, boleh, label_hak

from .context_processors import KOMPONEN
from .forms import (
    AgendaForm, ButirDataForm, DokumenForm, JawabKlarifikasiForm,
    LogVerifikasiForm, StatusTindakLanjutForm, TindakLanjutForm, PencapaianDataForm
)
from .indikator import DAFTAR_INDIKATOR, hitung_triwulan, rekap_tahunan
from .models import (
    PILIHAN_KATEGORI_DOKUMEN, PILIHAN_STATUS_DATA, PILIHAN_STATUS_TL,
    STATUS_BELUM, STATUS_TERVERIFIKASI, TL_SELESAI,
    Agenda, ButirData, Dokumen, LogVerifikasi, TargetIndikator, TindakLanjut,
    tahun_default, triwulan_sekarang, JenisData, PencapaianData
)


# ===========================================================================
# A. KELAS DASAR GENERIK
# ===========================================================================
class KomponenMixin(LoginRequiredMixin):
    """Dasar semua halaman komponen.

    Atribut yang diisi kelas turunan:
        komponen    kunci di accounts/permissions.KEBIJAKAN (mis. "matriks")
        prefix      awalan nama URL (mis. "matriks" -> matriks_daftar)
        judul       judul halaman
        url_sukses  nama URL tujuan setelah simpan; bila kosong -> <prefix>_daftar
    LoginRequiredMixin otomatis mengarahkan tamu ke halaman login.
    """

    komponen = ""
    prefix = ""
    judul = ""
    url_sukses = None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"judul": self.judul, "komponen": self.komponen, "prefix": self.prefix, "aktif": self.komponen})
        return ctx

    def get_success_url(self):
        return reverse(self.url_sukses or f"{self.prefix}_daftar")


class PesanMixin:
    """Menampilkan pesan sukses (toast) setelah form berhasil diproses."""

    pesan_sukses = "Data berhasil disimpan."

    def form_valid(self, form):
        respons = super().form_valid(form)
        messages.success(self.request, self.pesan_sukses)
        return respons


class FormUserMixin:
    """Meneruskan `user` ke form (dipakai ButirDataForm)."""

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class DaftarView(KomponenMixin, ListView):
    """Halaman tabel generik dengan pencarian, filter, dan paginasi.

    Atribut konfigurasi:
        kolom         [(label, "atribut" | "relasi.atribut" [, "badge"]), ...]
        cari          daftar field untuk pencarian teks (?q=)
        filter_status (nama_field, pilihan) -> dropdown status (?status=)
        filter_waktu  True -> tampilkan filter tahun & triwulan
        relasi        select_related agar query lebih hemat
        jalur_opd     jalur relasi ke OPD untuk membatasi data PIC (None = tak dibatasi)
        aksi_baris    tombol tambahan per baris: [(label, nama_url, aksi_izin, ikon)]
    """

    template_name = "crud/daftar.html"
    paginate_by = 15
    kolom = []
    cari = []
    filter_status = None
    filter_waktu = False
    relasi = ()
    jalur_opd = "opd"
    aksi_baris = ()

    # --- Query -----------------------------------------------------------
    def get_queryset(self):
        qs = super().get_queryset()
        if self.relasi:
            qs = qs.select_related(*self.relasi)
        if self.jalur_opd:
            qs = batasi_opd(self.request.user, qs, self.jalur_opd)

        get = self.request.GET
        q = get.get("q", "").strip()
        if q and self.cari:
            kondisi = Q()
            for field in self.cari:
                kondisi |= Q(**{f"{field}__icontains": q})
            qs = qs.filter(kondisi)

        status = get.get("status", "")
        if status and self.filter_status:
            qs = qs.filter(**{self.filter_status[0]: status})

        if self.filter_waktu:
            if get.get("tahun", "").isdigit():
                qs = qs.filter(tahun=int(get["tahun"]))
            if get.get("triwulan", "").isdigit():
                qs = qs.filter(triwulan=int(get["triwulan"]))
        return qs

    # --- Pembuatan sel tabel --------------------------------------------
    @staticmethod
    def _ambil(obj, jalur):
        """Menelusuri 'relasi.atribut' secara berantai; None bila ada yang kosong."""
        nilai = obj
        for bagian in jalur.split("."):
            if nilai is None:
                return None
            nilai = getattr(nilai, bagian)
            if callable(nilai):
                nilai = nilai()
        return nilai

    def _sel(self, obj, kolom):
        jalur = kolom[1]
        tipe = kolom[2] if len(kolom) > 2 else "teks"
        nilai = self._ambil(obj, jalur)
        teks = nilai
        # Field ber-choices / properti kita punya get_<nama>_display()
        tampil = getattr(obj, f"get_{jalur}_display", None) if "." not in jalur else None
        if tampil:
            teks = tampil()
        if isinstance(teks, bool):
            teks = "Ya" if teks else "Tidak"
        if teks in (None, ""):
            teks = "–"
        elif isinstance(teks, str):
            teks = Truncator(teks).chars(90)
        return {"teks": teks, "tipe": tipe, "kunci": str(nilai)}

    # --- Konteks template ------------------------------------------------
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        baris = []
        for obj in ctx["object_list"]:
            tambahan = []
            for label, nama_url, aksi, ikon in self.aksi_baris:
                if boleh(user, self.komponen, aksi, obj):
                    tambahan.append({"label": label, "url": reverse(nama_url, args=[obj.pk]), "ikon": ikon})
            baris.append({
                "obj": obj,
                "sel": [self._sel(obj, k) for k in self.kolom],
                "ubah": boleh(user, self.komponen, "ubah", obj),
                "hapus": boleh(user, self.komponen, "hapus", obj),
                "tambahan": tambahan,
            })

        qs_tanpa_halaman = self.request.GET.copy()
        qs_tanpa_halaman.pop("page", None)
        tahun = tahun_default()
        ctx.update({
            "kepala": [k[0] for k in self.kolom],
            "baris": baris,
            "bisa_tambah": boleh(user, self.komponen, "tambah"),
            "filter_status": self.filter_status[1] if self.filter_status else None,
            "filter_waktu": self.filter_waktu,
            "tahun_opsi": range(tahun - 2, tahun + 3),
            "q": self.request.GET.get("q", ""),
            "status_dipilih": self.request.GET.get("status", ""),
            "tahun_dipilih": self.request.GET.get("tahun", ""),
            "triwulan_dipilih": self.request.GET.get("triwulan", ""),
            "qs": qs_tanpa_halaman.urlencode(),
            "dibatasi": user.peran == PERAN_PIC and not user.is_superuser and self.jalur_opd,
            "tanpa_opd": user.peran == PERAN_PIC and not user.opd_id,
        })
        return ctx


class TambahView(PesanMixin, KomponenMixin, CreateView):
    """Halaman tambah data generik (cek izin 'tambah')."""

    template_name = "crud/form.html"
    pesan_sukses = "Data baru berhasil ditambahkan."

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not boleh(request.user, self.komponen, "tambah"):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"aksi_label": "Tambah", "batal_url": self.get_success_url()})
        return ctx


class UbahView(PesanMixin, KomponenMixin, UpdateView):
    """Halaman ubah data generik (cek izin per-objek)."""

    template_name = "crud/form.html"
    aksi_ubah = "ubah"        # aksi izin yang dicek; PIC memakai "jawab"/"perbarui_status"
    jalur_opd = "opd"
    pesan_sukses = "Perubahan berhasil disimpan."

    def get_queryset(self):
        qs = super().get_queryset()
        if self.jalur_opd:
            qs = batasi_opd(self.request.user, qs, self.jalur_opd)
        return qs

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not boleh(self.request.user, self.komponen, self.aksi_ubah, obj):
            raise PermissionDenied
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"aksi_label": "Ubah", "batal_url": self.get_success_url()})
        return ctx


class HapusView(PesanMixin, KomponenMixin, DeleteView):
    """Halaman konfirmasi hapus generik."""

    template_name = "crud/hapus.html"
    jalur_opd = "opd"
    pesan_sukses = "Data berhasil dihapus."

    def get_queryset(self):
        qs = super().get_queryset()
        if self.jalur_opd:
            qs = batasi_opd(self.request.user, qs, self.jalur_opd)
        return qs

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not boleh(self.request.user, self.komponen, "hapus", obj):
            raise PermissionDenied
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({"aksi_label": "Hapus", "batal_url": self.get_success_url()})
        return ctx


# ===========================================================================
# B. DASHBOARD
# ===========================================================================
class DashboardView(LoginRequiredMixin, TemplateView):
    """Beranda: ringkasan angka penting + 6 kartu komponen (seperti Gambar 4.6)."""

    template_name = "workspace/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        hari = timezone.localdate()
        tahun, tw = tahun_default(), triwulan_sekarang()

        # Data dibatasi sesuai peran (PIC hanya OPD-nya)
        butir = batasi_opd(user, ButirData.objects.all(), "opd")
        butir_tw = butir.filter(tahun=tahun, triwulan=tw)
        log = batasi_opd(user, LogVerifikasi.objects.all(), "butir__opd")
        tl = batasi_opd(user, TindakLanjut.objects.all(), "opd")

        klarifikasi_menunggu = log.exclude(catatan_klarifikasi="").filter(jawaban_klarifikasi="").count()
        tl_terbuka = tl.exclude(status=TL_SELESAI).count()
        agenda_mendatang = Agenda.objects.filter(tanggal__gte=hari)[:5]
        total_butir = butir_tw.count()
        diterima = butir_tw.exclude(status=STATUS_BELUM).count()

        statistik = [
            {"label": "Butir data triwulan ini", "nilai": total_butir, "catatan": f"{diterima} sudah diterima"},
            {"label": "Terverifikasi", "nilai": butir_tw.filter(status=STATUS_TERVERIFIKASI).count(), "catatan": "lolos pemeriksaan"},
            {"label": "Klarifikasi menunggu", "nilai": klarifikasi_menunggu, "catatan": "belum dijawab PIC"},
            {"label": "Tindak lanjut terbuka", "nilai": tl_terbuka, "catatan": "belum selesai"},
        ]

        # Teks ringkas di tiap kartu komponen
        info = {
            "matriks": f"{total_butir} butir data TW{tw}",
            "verifikasi": f"{klarifikasi_menunggu} klarifikasi menunggu",
            "tindaklanjut": f"{tl_terbuka} tindak lanjut terbuka",
            "kalender": f"{Agenda.objects.filter(tanggal__gte=hari).count()} agenda mendatang",
            "pustaka": f"{Dokumen.objects.count()} dokumen",
            "indikator": "H1-H3 dan P1-P3",
        }
        kartu = [
            {"kunci": k, "nomor": n, "judul": j, "url": u, "ikon": i, "deskripsi": d,
             "hak": label_hak(user, k), "info": info[k]}
            for k, n, j, u, i, d in KOMPONEN
        ]

        ctx.update({
            "aktif": "dashboard",
            "tahun": tahun, "triwulan": tw,
            "statistik": statistik,
            "kartu": kartu,
            "agenda_mendatang": agenda_mendatang,
            "jatuh_tempo": butir.filter(
                tanggal_diterima__isnull=True, batas_waktu__gte=hari, batas_waktu__lte=hari + timedelta(days=14)
            ).select_related("opd").order_by("batas_waktu")[:6],
            "indikator": hitung_triwulan(tahun, tw),
        })
        return ctx


# ===========================================================================
# C. KOMPONEN 1 - MATRIKS KEBUTUHAN DATA DAN JADWAL
# ===========================================================================
class MatriksCfg:
    """Konfigurasi bersama semua view komponen 1."""
    komponen = "matriks"
    prefix = "matriks"
    model = ButirData
    judul = "Matriks Kebutuhan Data dan Jadwal"


class MatriksSimpanMixin:
    """Untuk PIC: paksa OPD = OPD akun, dan PIC = akun itu sendiri."""

    def form_valid(self, form):
        user = self.request.user
        if user.peran == PERAN_PIC and not user.is_superuser:
            form.instance.opd = user.opd
            if not form.instance.pic_id:
                form.instance.pic = user
        return super().form_valid(form)


class MatriksDaftar(MatriksCfg, DaftarView):
    cari = ["kode", "jenis_data", "sektor", "opd__nama", "opd__singkatan"]
    filter_status = ("status", PILIHAN_STATUS_DATA)
    filter_waktu = True
    relasi = ("opd", "pic")
    kolom = [
        ("Kode", "kode"), ("Jenis data", "jenis_data"), ("Sektor", "sektor"),
        ("OPD/Instansi", "opd.singkatan"), ("PIC", "pic.nama_tampil"),
        ("Periode", "periode_referensi"), ("Cakupan", "cakupan"), ("Satuan", "satuan"),
        ("Batas waktu", "batas_waktu"), ("Diterima", "tanggal_diterima"),
        ("Status", "status", "badge"),
    ]


class MatriksTambah(MatriksSimpanMixin, FormUserMixin, MatriksCfg, TambahView):
    form_class = ButirDataForm


class MatriksUbah(MatriksSimpanMixin, FormUserMixin, MatriksCfg, UbahView):
    form_class = ButirDataForm


class MatriksHapus(MatriksCfg, HapusView):
    pass


# ===========================================================================
# D. KOMPONEN 2 - LOG VERIFIKASI DAN PERMINTAAN ULANG
# ===========================================================================
class VerifikasiCfg:
    komponen = "verifikasi"
    prefix = "verifikasi"
    model = LogVerifikasi
    judul = "Log Verifikasi dan Permintaan Ulang"
    jalur_opd = "butir__opd"     # PIC hanya melihat log butir milik OPD-nya


class VerifikasiSimpanMixin:
    """Mencatat siapa yang melakukan verifikasi."""

    def form_valid(self, form):
        form.instance.diverifikasi_oleh = self.request.user
        return super().form_valid(form)


class VerifikasiDaftar(VerifikasiCfg, DaftarView):
    cari = ["butir__kode", "butir__jenis_data", "butir__opd__singkatan", "catatan_klarifikasi"]
    relasi = ("butir", "butir__opd")
    kolom = [
        ("Kode butir", "butir.kode"), ("Jenis data", "butir.jenis_data"),
        ("OPD/Instansi", "butir.opd.singkatan"), ("Tanggal", "tanggal"),
        ("Hasil", "hasil", "badge"), ("Klarifikasi", "status_klarifikasi", "badge"),
        ("Catatan", "catatan_klarifikasi"),
    ]
    aksi_baris = [("Jawab klarifikasi", "verifikasi_jawab", "jawab", "balas")]


class VerifikasiTambah(VerifikasiSimpanMixin, VerifikasiCfg, TambahView):
    form_class = LogVerifikasiForm


class VerifikasiUbah(VerifikasiSimpanMixin, VerifikasiCfg, UbahView):
    form_class = LogVerifikasiForm


class VerifikasiHapus(VerifikasiCfg, HapusView):
    pass


class VerifikasiJawab(VerifikasiCfg, UbahView):
    """PIC menjawab klarifikasi (hanya satu kolom yang bisa diisi)."""

    form_class = JawabKlarifikasiForm
    aksi_ubah = "jawab"
    judul = "Jawab Klarifikasi"
    pesan_sukses = "Jawaban klarifikasi terkirim."

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        log = self.object
        ctx["aksi_label"] = ""
        ctx["konteks"] = [
            ("Butir data", str(log.butir)),
            ("OPD/Instansi", str(log.butir.opd)),
            ("Tanggal verifikasi", log.tanggal),
            ("Hasil pemeriksaan", log.get_hasil_display()),
            ("Catatan klarifikasi", log.catatan_klarifikasi or "–"),
        ]
        return ctx


# ===========================================================================
# E. KOMPONEN 3 - MATRIKS TINDAK LANJUT FORUM
# ===========================================================================
class TindakLanjutCfg:
    komponen = "tindaklanjut"
    prefix = "tindaklanjut"
    model = TindakLanjut
    judul = "Matriks Tindak Lanjut Forum"


class TindakLanjutDaftar(TindakLanjutCfg, DaftarView):
    cari = ["isu", "tindak_lanjut", "opd__singkatan", "penanggung_jawab__username", "penanggung_jawab__first_name"]
    filter_status = ("status", PILIHAN_STATUS_TL)
    filter_waktu = True
    relasi = ("opd", "penanggung_jawab")
    kolom = [
        ("Isu / temuan", "isu"), ("Tindak lanjut", "tindak_lanjut"),
        ("OPD/Instansi", "opd.singkatan"), ("Penanggung jawab", "penanggung_jawab.nama_tampil"),
        ("Batas waktu", "batas_waktu"), ("Status", "status", "badge"),
    ]
    aksi_baris = [("Perbarui status", "tindaklanjut_status", "perbarui_status", "ubah")]


class TindakLanjutTambah(TindakLanjutCfg, TambahView):
    form_class = TindakLanjutForm


class TindakLanjutUbah(TindakLanjutCfg, UbahView):
    form_class = TindakLanjutForm


class TindakLanjutHapus(TindakLanjutCfg, HapusView):
    pass


class TindakLanjutStatus(TindakLanjutCfg, UbahView):
    """PIC memperbarui status tindak lanjut OPD-nya."""

    form_class = StatusTindakLanjutForm
    aksi_ubah = "perbarui_status"
    judul = "Perbarui Status Tindak Lanjut"
    pesan_sukses = "Status tindak lanjut diperbarui."

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tl = self.object
        ctx["aksi_label"] = ""
        ctx["konteks"] = [
            ("Isu / temuan", tl.isu),
            ("Tindak lanjut", tl.tindak_lanjut),
            ("Batas waktu", tl.batas_waktu),
        ]
        return ctx


# ===========================================================================
# F. KOMPONEN 4 - KALENDER KOORDINASI DAN PENGINGAT
# ===========================================================================
NAMA_BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
              "Agustus", "September", "Oktober", "November", "Desember"]
NAMA_HARI = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]


class KalenderView(KomponenMixin, TemplateView):
    """Kalender bulanan: agenda + jumlah batas waktu data tiap tanggal."""

    komponen = "kalender"
    prefix = "agenda"
    judul = "Kalender Koordinasi dan Pengingat"
    template_name = "workspace/kalender.html"

    def _awal_bulan(self) -> date:
        """Membaca ?bulan=YYYY-MM; bila salah/kosong pakai bulan ini."""
        try:
            tahun, bulan = self.request.GET.get("bulan", "").split("-")
            return date(int(tahun), int(bulan), 1)
        except ValueError:
            return timezone.localdate().replace(day=1)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        hari = timezone.localdate()
        awal = self._awal_bulan()

        # Daftar minggu (tiap minggu = 7 tanggal, Senin-Minggu), termasuk
        # tanggal bulan sebelum/sesudahnya agar grid penuh.
        minggu = calendar.Calendar(firstweekday=0).monthdatescalendar(awal.year, awal.month)
        mulai, akhir = minggu[0][0], minggu[-1][-1]

        # Kumpulkan peristiwa per tanggal
        peristiwa = defaultdict(list)
        for a in Agenda.objects.filter(tanggal__range=(mulai, akhir)):
            peristiwa[a.tanggal].append({"judul": a.judul, "jenis": a.jenis, "jam": a.jam, "pk": a.pk})
        batas = (
            batasi_opd(user, ButirData.objects.filter(batas_waktu__range=(mulai, akhir)), "opd")
            .values("batas_waktu").annotate(n=Count("id")).order_by()
        )
        for r in batas:
            peristiwa[r["batas_waktu"]].append({"judul": f"{r['n']} batas data", "jenis": "batas", "jam": None, "pk": None})

        grid = [
            [{"tanggal": d, "bulan_ini": d.month == awal.month, "hari_ini": d == hari, "acara": peristiwa.get(d, [])} for d in pekan]
            for pekan in minggu
        ]
        sebelum = (awal - timedelta(days=1)).replace(day=1)
        sesudah = (awal + timedelta(days=32)).replace(day=1)

        ctx.update({
            "grid": grid,
            "nama_hari": NAMA_HARI,
            "judul_bulan": f"{NAMA_BULAN[awal.month - 1]} {awal.year}",
            "bulan_sebelum": sebelum.strftime("%Y-%m"),
            "bulan_sesudah": sesudah.strftime("%Y-%m"),
            "agenda_bulan": Agenda.objects.filter(tanggal__year=awal.year, tanggal__month=awal.month),
            "bisa_tambah": boleh(user, "kalender", "tambah"),
            "bisa_ubah": boleh(user, "kalender", "ubah"),
        })
        return ctx


class AgendaCfg:
    komponen = "kalender"
    prefix = "agenda"
    model = Agenda
    judul = "Agenda"
    url_sukses = "kalender"
    jalur_opd = None


class AgendaSimpanMixin:
    def form_valid(self, form):
        if not form.instance.pk:
            form.instance.dibuat_oleh = self.request.user
        return super().form_valid(form)


class AgendaTambah(AgendaSimpanMixin, AgendaCfg, TambahView):
    form_class = AgendaForm

    def get_initial(self):
        """Klik tanggal di kalender -> ?tanggal=YYYY-MM-DD terisi otomatis."""
        initial = super().get_initial()
        try:
            initial["tanggal"] = date.fromisoformat(self.request.GET.get("tanggal", ""))
        except ValueError:
            pass
        return initial


class AgendaUbah(AgendaSimpanMixin, AgendaCfg, UbahView):
    form_class = AgendaForm


class AgendaHapus(AgendaCfg, HapusView):
    pass


# ===========================================================================
# G. KOMPONEN 5 - PUSTAKA DOKUMEN
# ===========================================================================
class PustakaView(KomponenMixin, ListView):
    """Galeri kartu dokumen dengan filter kategori dan pencarian."""

    komponen = "pustaka"
    prefix = "pustaka"
    judul = "Pustaka Dokumen"
    model = Dokumen
    template_name = "workspace/pustaka.html"
    paginate_by = 12

    def get_queryset(self):
        qs = super().get_queryset().select_related("diunggah_oleh")
        kategori = self.request.GET.get("kategori", "")
        if kategori:
            qs = qs.filter(kategori=kategori)
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(judul__icontains=q) | Q(deskripsi__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        jumlah = dict(Dokumen.objects.values_list("kategori").annotate(n=Count("id")).order_by())
        qs = self.request.GET.copy()
        qs.pop("page", None)
        ctx.update({
            "kategori_opsi": [(kode, nama, jumlah.get(kode, 0)) for kode, nama in PILIHAN_KATEGORI_DOKUMEN],
            "kategori_dipilih": self.request.GET.get("kategori", ""),
            "q": self.request.GET.get("q", ""),
            "total": sum(jumlah.values()),
            "bisa_tambah": boleh(self.request.user, "pustaka", "tambah"),
            "bisa_ubah": boleh(self.request.user, "pustaka", "ubah"),
            "qs": qs.urlencode(),
        })
        return ctx


class PustakaCfg:
    komponen = "pustaka"
    prefix = "pustaka"
    model = Dokumen
    judul = "Dokumen"
    url_sukses = "pustaka"
    jalur_opd = None


class PustakaSimpanMixin:
    def form_valid(self, form):
        if not form.instance.pk:
            form.instance.diunggah_oleh = self.request.user
        return super().form_valid(form)


class PustakaTambah(PustakaSimpanMixin, PustakaCfg, TambahView):
    form_class = DokumenForm
    pesan_sukses = "Dokumen berhasil diunggah."


class PustakaUbah(PustakaSimpanMixin, PustakaCfg, UbahView):
    form_class = DokumenForm


class PustakaHapus(PustakaCfg, HapusView):
    def form_valid(self, form):
        """Hapus juga berkas fisiknya dari penyimpanan."""
        berkas = self.object.berkas
        respons = super().form_valid(form)
        berkas.delete(save=False)
        return respons


class PustakaUnduh(LoginRequiredMixin, View):
    """Unduh berkas lewat view (bukan URL media langsung) agar wajib login."""

    def get(self, request, pk):
        dokumen = get_object_or_404(Dokumen, pk=pk)
        try:
            berkas = dokumen.berkas.open("rb")
        except FileNotFoundError:
            raise Http404("Berkas tidak ditemukan di penyimpanan.")
        return FileResponse(berkas, as_attachment=True, filename=os.path.basename(dokumen.berkas.name))


# ===========================================================================
# H. KOMPONEN 6 - REKAP INDIKATOR
# ===========================================================================
def _baca_tahun(request) -> int:
    """Membaca ?tahun= (angka) atau memakai tahun berjalan."""
    nilai = request.GET.get("tahun", "") or request.POST.get("tahun", "")
    return int(nilai) if nilai.isdigit() else tahun_default()


class IndikatorView(KomponenMixin, TemplateView):
    """Tabel indikator x triwulan + kartu ringkas untuk satu triwulan."""

    komponen = "indikator"
    prefix = "indikator"
    judul = "Rekap Indikator"
    template_name = "workspace/indikator.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tahun = _baca_tahun(self.request)
        tw = int(self.request.GET["triwulan"]) if self.request.GET.get("triwulan", "") in ("1", "2", "3", "4") else triwulan_sekarang()
        ctx.update({
            "tahun": tahun, "triwulan": tw,
            "tahun_opsi": range(tahun_default() - 2, tahun_default() + 3),
            "baris": rekap_tahunan(tahun),
            "kartu": hitung_triwulan(tahun, tw),
            "bisa_ubah": boleh(self.request.user, "indikator", "ubah"),
        })
        return ctx


class TargetIndikatorView(KomponenMixin, TemplateView):
    """Form target indikator (6 indikator x 4 triwulan) - Project Leader/Tim Teknis."""

    komponen = "indikator"
    prefix = "indikator"
    judul = "Atur Target Indikator"
    template_name = "workspace/indikator_target.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not boleh(request.user, "indikator", "ubah"):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        tahun = _baca_tahun(self.request)
        tersimpan = {(t.kode, t.triwulan): t.target for t in TargetIndikator.objects.filter(tahun=tahun)}
        ctx.update({
            "tahun": tahun,
            "tahun_opsi": range(tahun_default() - 2, tahun_default() + 3),
            "baris": [
                {
                    "indikator": ind,
                    "sel": [
                        {"triwulan": tw, "nama": f"t_{ind.kode}_{tw}", "nilai": tersimpan.get((ind.kode, tw), "")}
                        for tw in (1, 2, 3, 4)
                    ],
                }
                for ind in DAFTAR_INDIKATOR
            ],
        })
        return ctx

    def post(self, request, *args, **kwargs):
        tahun = _baca_tahun(request)
        salah = 0
        for ind in DAFTAR_INDIKATOR:
            for tw in (1, 2, 3, 4):
                mentah = request.POST.get(f"t_{ind.kode}_{tw}", "").strip().replace(",", ".")
                kunci = {"kode": ind.kode, "tahun": tahun, "triwulan": tw}
                if mentah == "":
                    TargetIndikator.objects.filter(**kunci).delete()   # kosong = hapus target
                    continue
                try:
                    TargetIndikator.objects.update_or_create(**kunci, defaults={"target": Decimal(mentah)})
                except (InvalidOperation, ValueError):
                    salah += 1
        if salah:
            messages.warning(request, f"{salah} isian bukan angka yang valid dan dilewati.")
        else:
            messages.success(request, f"Target indikator tahun {tahun} berhasil disimpan.")
        return redirect(f"{reverse('indikator')}?tahun={tahun}")

# ===========================================================================
# I. KOMPONEN 7 - input data OPD terkait
# ===========================================================================
# Dictionary statis untuk jenis data di backend (jaga-jaga jika dipanggil AJAX)
DATA_JENIS_DATA = {
    "Dinas Pertanian": [
        {"id": "Luas Panen Padi", "nama_jenis_data": "Luas Panen Padi"},
        {"id": "Luas Panen Jagung", "nama_jenis_data": "Luas Panen Jagung"},
        {"id": "Produksi Hortikultura Semusim", "nama_jenis_data": "Produksi Hortikultura Semusim"},
        {"id": "Produksi Hortikultura Tahunan", "nama_jenis_data": "Produksi Hortikultura Tahunan"},
        {"id": "Harga Hortikultura Semusim", "nama_jenis_data": "Harga Hortikultura Semusim"},
        {"id": "Harga Hortikultura Tahunan", "nama_jenis_data": "Harga Hortikultura Tahunan"}
    ],
    "Dinas Perkebunan": [
        {"id": "Produksi Perkebunan Semusim", "nama_jenis_data": "Produksi Perkebunan Semusim"},
        {"id": "Produksi Perkebunan Tahunan", "nama_jenis_data": "Produksi Perkebunan Tahunan"},
        {"id": "Harga Perkebunan Semusim", "nama_jenis_data": "Harga Perkebunan Semusim"},
        {"id": "Harga Perkebunan Tahunan", "nama_jenis_data": "Harga Perkebunan Tahunan"}
    ],
    "Dinas Perikanan": [
        {"id": "Produksi Perikanan Tangkap", "nama_jenis_data": "Produksi Perikanan Tangkap"},
        {"id": "Harga Perikanan Tangkap", "nama_jenis_data": "Harga Perikanan Tangkap"},
        {"id": "Produksi Perikanan Budidaya", "nama_jenis_data": "Produksi Perikanan Budidaya"},
        {"id": "Harga Perikanan Budidaya", "nama_jenis_data": "Harga Perikanan Budidaya"}
    ],
    "KPHL Pasaman Raya": [
        {"id": "Produksi Komoditas Kehutanan", "nama_jenis_data": "Produksi Komoditas Kehutanan"},
        {"id": "Harga Komoditras Kehutanan", "nama_jenis_data": "Harga Komoditras Kehutanan"}
    ],
    "Dinas PU": [
        {"id": "Proyek yang sedang berjalan", "nama_jenis_data": "Proyek yang sedang berjalan"},
        {"id": "Anggaran Proyek Berjalan", "nama_jenis_data": "Anggaran Proyek Berjalan"}
    ]
}
def get_jenis_data_by_opd(request):
    opd_id = request.GET.get('opd_id')
    jenis_data = JenisData.objects.filter(opd_id=opd_id).values('id', 'nama_jenis_data')
    return JsonResponse(list(jenis_data), safe=False)

def tambah_pencapaian_view(request):
    if request.method == 'POST':
        form = PencapaianDataForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Data OPD Berhasil ditambahkan')
            return redirect('daftar_pencapaian') # Sesuaikan url redirect setelah sukses
    else:
        form = PencapaianDataForm()
    
    # PASTIKAN DICTIONARY 'context' DIDEFINISIKAN DI SINI (sebelum return render)
    context = {
        'form': form,
        'aktif': 'tambah_pencapaian'  # Agar menu aktif menyala di sidebar
    }
    
    return render(request, 'crud/form_pencapaian.html', context)

# ===========================================================================
# I. KOMPONEN 8 - Tabel Hasil Input Data OPD
# ===========================================================================
class HasilDataOpd(KomponenMixin, TemplateView):
    """Tabel indikator x triwulan + kartu ringkas untuk satu triwulan."""

    komponen = "data_hasil"
    prefix = "data_hasil"
    judul = "Data Hasil Input OPD"
    template_name = "crud/form_pencapaian.html"
    
def daftar_pencapaian_view(request):
    # Mengambil semua data pencapaian dari database
    pencapaian_list = PencapaianData.objects.all()
    
    context = {
        'pencapaian_list': pencapaian_list,
        'aktif': 'daftar_pencapaian' # Untuk menandai menu aktif di sidebar
    }
    return render(request, 'crud/daftar_pencapaian.html', context)

class EditPencapaianView(LoginRequiredMixin, UpdateView):
    model = PencapaianData
    form_class = PencapaianDataForm
    template_name = "crud/form_pencapaian.html"  # template yang sudah ada di proyek
    success_url = reverse_lazy("daftar_pencapaian")  # sesuai name di workspace/urls.py


class HapusPencapaianView(LoginRequiredMixin, DeleteView):
    model = PencapaianData
    template_name = "crud/hapus.html"  # template yang sudah ada di proyek
    success_url = reverse_lazy("daftar_pencapaian")  # sesuai name di workspace/urls.py

# ===========================================================================
# I. KOMPONEN 9 - Edit Hasil Input Data OPD
# ===========================================================================
class EditPencapaianView(LoginRequiredMixin, UpdateView):
    model = PencapaianData
    form_class = PencapaianDataForm
    template_name = "crud/edit_pencapaian.html"  # template khusus edit
    success_url = reverse_lazy("daftar_pencapaian")  #[cite: 3]


# ===========================================================================
# I. KOMPONEN 10 - DownloadData OPD
# ===========================================================================
@login_required
def export_pencapaian_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Pencapaian Data OPD"

    # Header kolom sesuai tabel di halaman
    headers = ["NO", "OPD", "JENIS DATA", "TAHUN", "TRIWULAN", "NILAI"]
    ws.append(headers)

    # Styling baris header
    header_fill = PatternFill(start_color="FDEEE3", end_color="FDEEE3", fill_type="solid")
    header_font = Font(bold=True, color="333333")
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Ambil semua data (sesuaikan urutan dengan view daftar Anda)
    queryset = PencapaianData.objects.all().order_by("id")

    for idx, data in enumerate(queryset, start=1):
        ws.append([
            idx,
            str(data.opd),
            str(data.jenis_data),
            data.tahun,
            str(data.triwulan),
            data.nilai,
        ])
        # Format pemisah ribuan pada kolom NILAI (kolom ke-6 / F)
        ws.cell(row=idx + 1, column=6).number_format = "#,##0"

    # Atur lebar kolom otomatis agar tidak terpotong
    for col in ws.columns:
        max_length = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = max_length + 4

    # Siapkan respons unduhan file .xlsx
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="daftar_pencapaian_opd.xlsx"'
    wb.save(response)
    return response