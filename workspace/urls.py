"""
Routing URL aplikasi `workspace`.

Pola penamaan: <komponen>_<aksi>, mis. matriks_daftar, matriks_tambah.
Nama inilah yang dipakai di template: {% url 'matriks_tambah' %}
"""
from django.urls import path

from . import views as v

urlpatterns = [
    path("", v.DashboardView.as_view(), name="dashboard"),

    # 1. Matriks Kebutuhan Data dan Jadwal
    path("matriks/", v.MatriksDaftar.as_view(), name="matriks_daftar"),
    path("matriks/tambah/", v.MatriksTambah.as_view(), name="matriks_tambah"),
    path("matriks/<int:pk>/ubah/", v.MatriksUbah.as_view(), name="matriks_ubah"),
    path("matriks/<int:pk>/hapus/", v.MatriksHapus.as_view(), name="matriks_hapus"),

    # 2. Log Verifikasi dan Permintaan Ulang
    path("verifikasi/", v.VerifikasiDaftar.as_view(), name="verifikasi_daftar"),
    path("verifikasi/tambah/", v.VerifikasiTambah.as_view(), name="verifikasi_tambah"),
    path("verifikasi/<int:pk>/ubah/", v.VerifikasiUbah.as_view(), name="verifikasi_ubah"),
    path("verifikasi/<int:pk>/hapus/", v.VerifikasiHapus.as_view(), name="verifikasi_hapus"),
    path("verifikasi/<int:pk>/jawab/", v.VerifikasiJawab.as_view(), name="verifikasi_jawab"),

    # 3. Matriks Tindak Lanjut Forum
    path("tindak-lanjut/", v.TindakLanjutDaftar.as_view(), name="tindaklanjut_daftar"),
    path("tindak-lanjut/tambah/", v.TindakLanjutTambah.as_view(), name="tindaklanjut_tambah"),
    path("tindak-lanjut/<int:pk>/ubah/", v.TindakLanjutUbah.as_view(), name="tindaklanjut_ubah"),
    path("tindak-lanjut/<int:pk>/hapus/", v.TindakLanjutHapus.as_view(), name="tindaklanjut_hapus"),
    path("tindak-lanjut/<int:pk>/status/", v.TindakLanjutStatus.as_view(), name="tindaklanjut_status"),

    # 4. Kalender Koordinasi dan Pengingat
    path("kalender/", v.KalenderView.as_view(), name="kalender"),
    path("kalender/agenda/tambah/", v.AgendaTambah.as_view(), name="agenda_tambah"),
    path("kalender/agenda/<int:pk>/ubah/", v.AgendaUbah.as_view(), name="agenda_ubah"),
    path("kalender/agenda/<int:pk>/hapus/", v.AgendaHapus.as_view(), name="agenda_hapus"),

    # 5. Pustaka Dokumen
    path("pustaka/", v.PustakaView.as_view(), name="pustaka"),
    path("pustaka/tambah/", v.PustakaTambah.as_view(), name="pustaka_tambah"),
    path("pustaka/<int:pk>/ubah/", v.PustakaUbah.as_view(), name="pustaka_ubah"),
    path("pustaka/<int:pk>/hapus/", v.PustakaHapus.as_view(), name="pustaka_hapus"),
    path("pustaka/<int:pk>/unduh/", v.PustakaUnduh.as_view(), name="pustaka_unduh"),

    # 6. Rekap Indikator
    path("indikator/", v.IndikatorView.as_view(), name="indikator"),
    path("indikator/target/", v.TargetIndikatorView.as_view(), name="indikator_target"),

    # 7. Pencapaian Data
    path('tambah-data/', v.tambah_pencapaian_view, name='tambah_pencapaian'),
    path('data-pencapaian/', v.daftar_pencapaian_view, name='daftar_pencapaian'), # URL Tabel
    path('data-pencapaian/<int:pk>/edit/', v.EditPencapaianView.as_view(), name='edit_pencapaian'),
    path('data-pencapaian/<int:pk>/hapus/', v.HapusPencapaianView.as_view(), name='hapus_pencapaian'),
    path('ajax/get-jenis-data/', v.get_jenis_data_by_opd, name='get_jenis_data'),
    path('data-pencapaian/', v.HasilDataOpd.as_view(), name='data_hasil'),
    path("data-pencapaian/<int:pk>/edit/", v.EditPencapaianView.as_view(), name="edit_pencapaian"),  #[cite: 3, 7]
    path("data-pencapaian/export-excel/", v.export_pencapaian_excel, name="export_pencapaian_excel"),
]
