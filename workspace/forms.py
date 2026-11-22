"""
Form (formulir isian) untuk komponen RANAH.

Setiap form adalah ModelForm: Django otomatis membuat kolom isian dari
model. `GayaMixin` hanya menambahkan class CSS agar tampil sesuai tema.
"""
from django import forms

from accounts.models import PERAN_PIC, User

from .models import Agenda, ButirData, Dokumen, LogVerifikasi, TindakLanjut, PencapaianData, JenisData


def input_tanggal():
    """Widget tanggal HTML5 (kalender bawaan browser)."""
    return forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class GayaMixin:
    """Menambahkan class CSS 'input' / 'checkbox' ke semua widget form."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            kelas = "checkbox" if isinstance(field.widget, forms.CheckboxInput) else "input"
            field.widget.attrs["class"] = (field.widget.attrs.get("class", "") + " " + kelas).strip()


# ---------------------------------------------------------------------------
# Komponen 1
# ---------------------------------------------------------------------------
class ButirDataForm(GayaMixin, forms.ModelForm):
    """Form butir data.

    Untuk PIC, kolom `opd`, `pic`, dan `status` disembunyikan: OPD & PIC
    diisi otomatis dari akun PIC (lihat views.MatriksSimpanMixin), sedangkan
    status diatur sistem lewat proses verifikasi.
    """

    class Meta:
        model = ButirData
        fields = [
            "kode", "jenis_data", "sektor", "opd", "pic", "tahun", "triwulan",
            "periode_referensi", "cakupan", "satuan", "batas_waktu",
            "tanggal_diterima", "status", "catatan",
        ]
        widgets = {
            "batas_waktu": input_tanggal(),
            "tanggal_diterima": input_tanggal(),
            "catatan": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Pilihan PIC hanya pengguna ber-peran PIC.
        self.fields["pic"].queryset = User.objects.filter(peran=PERAN_PIC)
        if user is not None and user.peran == PERAN_PIC and not user.is_superuser:
            for nama in ("opd", "pic", "status"):
                self.fields.pop(nama)


# ---------------------------------------------------------------------------
# Komponen 2
# ---------------------------------------------------------------------------
class LogVerifikasiForm(GayaMixin, forms.ModelForm):
    """Form verifikasi oleh Tim Teknis."""

    class Meta:
        model = LogVerifikasi
        fields = ["butir", "tanggal", "lengkap", "periode_sesuai", "cakupan_sesuai", "satuan_sesuai", "catatan_klarifikasi"]
        widgets = {
            "tanggal": input_tanggal(),
            "catatan_klarifikasi": forms.Textarea(attrs={"rows": 4}),
        }


class JawabKlarifikasiForm(GayaMixin, forms.ModelForm):
    """Form sederhana: PIC hanya mengisi jawaban klarifikasi."""

    class Meta:
        model = LogVerifikasi
        fields = ["jawaban_klarifikasi"]
        widgets = {"jawaban_klarifikasi": forms.Textarea(attrs={"rows": 5})}


# ---------------------------------------------------------------------------
# Komponen 3
# ---------------------------------------------------------------------------
class TindakLanjutForm(GayaMixin, forms.ModelForm):
    """Form lengkap tindak lanjut (Tim Teknis)."""

    class Meta:
        model = TindakLanjut
        fields = ["isu", "tindak_lanjut", "agenda", "opd", "penanggung_jawab", "tahun", "triwulan", "batas_waktu", "status", "catatan"]
        widgets = {
            "batas_waktu": input_tanggal(),
            "tindak_lanjut": forms.Textarea(attrs={"rows": 3}),
            "catatan": forms.Textarea(attrs={"rows": 3}),
        }


class StatusTindakLanjutForm(GayaMixin, forms.ModelForm):
    """Form ringkas untuk PIC: hanya status & catatan perkembangan."""

    class Meta:
        model = TindakLanjut
        fields = ["status", "catatan"]
        widgets = {"catatan": forms.Textarea(attrs={"rows": 4})}


# ---------------------------------------------------------------------------
# Komponen 4
# ---------------------------------------------------------------------------
class AgendaForm(GayaMixin, forms.ModelForm):
    class Meta:
        model = Agenda
        fields = ["judul", "jenis", "tanggal", "jam", "lokasi", "deskripsi", "pengingat_hari"]
        widgets = {
            "tanggal": input_tanggal(),
            "jam": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "deskripsi": forms.Textarea(attrs={"rows": 3}),
        }


# ---------------------------------------------------------------------------
# Komponen 5
# ---------------------------------------------------------------------------
class DokumenForm(GayaMixin, forms.ModelForm):
    class Meta:
        model = Dokumen
        fields = ["judul", "kategori", "berkas", "deskripsi"]
        widgets = {"deskripsi": forms.Textarea(attrs={"rows": 3})}

# ---------------------------------------------------------------------------
# Komponen 7
# ---------------------------------------------------------------------------
OPD_CHOICES = [
    ('', '---------'),
    ('Dinas Pertanian', 'Dinas Pertanian'),
    ('Dinas Perkebunan', 'Dinas Perkebunan'),
    ('Dinas Perikanan', 'Dinas Perikanan'),
    ('KPHL Pasaman Raya', 'KPHL Pasaman Raya'),
    ('Dinas PU', 'Dinas PU'),
]

# Gabungkan semua pilihan jenis data agar valid saat divalidasi oleh Django di backend
ALL_JENIS_DATA_CHOICES = [
    ('', '---------'),
    # Dinas Pertanian
    ('Luas Panen Padi', 'Luas Panen Padi'),
    ('Luas Panen Jagung', 'Luas Panen Jagung'),
    ('Produksi Hortikultura Semusim', 'Produksi Hortikultura Semusim'),
    ('Produksi Hortikultura Tahunan', 'Produksi Hortikultura Tahunan'),
    ('Harga Hortikultura Semusim', 'Harga Hortikultura Semusim'),
    ('Harga Hortikultura Tahunan', 'Harga Hortikultura Tahunan'),
    # Dinas Perkebunan
    ('Produksi Perkebunan Semusim', 'Produksi Perkebunan Semusim'),
    ('Produksi Perkebunan Tahunan', 'Produksi Perkebunan Tahunan'),
    ('Harga Perkebunan Semusim', 'Harga Perkebunan Semusim'),
    ('Harga Perkebunan Tahunan', 'Harga Perkebunan Tahunan'),
    # Dinas Perikanan
    ('Produksi Perikanan Tangkap', 'Produksi Perikanan Tangkap'),
    ('Harga Perikanan Tangkap', 'Harga Perikanan Tangkap'),
    ('Produksi Perikanan Budidaya', 'Produksi Perikanan Budidaya'),
    ('Harga Perikanan Budidaya', 'Harga Perikanan Budidaya'),
    # KPHL Pasaman Raya
    ('Produksi Komoditas Kehutanan', 'Produksi Komoditas Kehutanan'),
    ('Harga Komoditras Kehutanan', 'Harga Komoditras Kehutanan'),
    # Dinas PU
    ('Proyek yang sedang berjalan', 'Proyek yang sedang berjalan'),
    ('Anggaran Proyek Berjalan', 'Anggaran Proyek Berjalan'),
]
class PencapaianDataForm(GayaMixin,forms.ModelForm):
    opd = forms.ChoiceField(
        choices=OPD_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_opd'})
    )
    jenis_data = forms.ChoiceField(
        choices=ALL_JENIS_DATA_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_jenis_data'})
    )

    class Meta:
        model = PencapaianData
        fields = ['opd', 'jenis_data', 'tahun', 'triwulan', 'nilai']
        widgets = {
            'tahun': forms.NumberInput(attrs={'class': 'form-control'}),
            'triwulan': forms.Select(attrs={'class': 'form-control'}),
            'nilai': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Jika ingin membatasi jenis data saat form dimuat ulang/validasi
        if 'opd' in self.data:
            try:
                opd_id = int(self.data.get('opd'))
                self.fields['jenis_data'].queryset = JenisData.objects.filter(opd_id=opd_id)
            except (ValueError, TypeError):
                self.fields['jenis_data'].queryset = JenisData.objects.none()
        elif self.instance.pk:
            opd_val = getattr(self.instance, "opd", None)
            if isinstance(opd_val, str):
                # Sesuaikan jika JenisData punya field nama/foreignkey OPD, misal:
                # self.fields['jenis_data'].queryset = JenisData.objects.filter(opd__nama=opd_val)
                self.fields['jenis_data'].queryset = JenisData.objects.all()
            elif opd_val is not None:
                self.fields['jenis_data'].queryset = JenisData.objects.filter(opd=opd_val)
            else:
                self.fields['jenis_data'].queryset = JenisData.objects.none()

# ---------------------------------------------------------------------------
# Komponen edit Data Pencapaian
# ---------------------------------------------------------------------------
class EditPencapaianForm(forms.ModelForm):
    class Meta:
        model = PencapaianData
        fields = ["opd", "jenis_data", "tahun", "triwulan", "nilai"]  #

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Kunci OPD dan Jenis Data agar tidak bisa diubah
        for nama_field in ("opd", "jenis_data"):
            if nama_field in self.fields:
                self.fields[nama_field].disabled = True
                self.fields[nama_field].widget.attrs["readonly"] = True