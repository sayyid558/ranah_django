"""
Matriks hak akses RANAH (implementasi tabel "Pengguna dan Hak Akses").

Konsep:
  * Semua pengguna yang sudah login boleh MELIHAT setiap komponen
    (PIC OPD hanya melihat baris milik OPD-nya, lihat `batasi_opd`).
  * "sunting"  = peran yang boleh menambah/mengubah/menghapus SEMUA data.
  * "opd"      = peran yang hanya boleh melakukan aksi tertentu pada data
                 milik OPD-nya sendiri.
  * Superuser selalu boleh.

Aksi yang dikenal fungsi `boleh()`:
    lihat | tambah | ubah | hapus | jawab | perbarui_status

Mengubah kebijakan cukup dengan mengedit dictionary KEBIJAKAN di bawah.
"""
from .models import (
    PERAN_ADMIN, PERAN_HUMAS, PERAN_LEADER, PERAN_PIC, PERAN_TEKNIS, PERAN_TI,
)

KEBIJAKAN = {
    # 1. Matriks Kebutuhan Data dan Jadwal
    "matriks": {
        "sunting": {PERAN_TEKNIS},
        "opd": {PERAN_PIC: {"tambah", "ubah"}},   # PIC menyunting lembar OPD-nya
    },
    # 2. Log Verifikasi dan Permintaan Ulang
    "verifikasi": {
        "sunting": {PERAN_TEKNIS},
        "opd": {PERAN_PIC: {"jawab"}},            # PIC melihat & menjawab klarifikasi
    },
    # 3. Matriks Tindak Lanjut Forum
    "tindaklanjut": {
        "sunting": {PERAN_TEKNIS},
        "opd": {PERAN_PIC: {"perbarui_status"}},  # PIC memperbarui status tindak lanjut
    },
    # 4. Kalender Koordinasi dan Pengingat
    "kalender": {
        "sunting": {PERAN_TEKNIS},
        "opd": {},
    },
    # 5. Pustaka Dokumen
    "pustaka": {
        "sunting": {PERAN_ADMIN, PERAN_TI, PERAN_HUMAS},
        "opd": {},
    },
    # 6. Rekap Indikator
    "indikator": {
        "sunting": {PERAN_LEADER, PERAN_TEKNIS},
        "opd": {},
    },
}


def _opd_id(obj):
    """Mencari id OPD dari sebuah objek.

    Objek bisa punya `opd_id` langsung (ButirData, TindakLanjut) atau
    lewat relasi `butir` (LogVerifikasi).
    """
    if obj is None:
        return None
    if hasattr(obj, "opd_id"):
        return obj.opd_id
    butir = getattr(obj, "butir", None)
    return butir.opd_id if butir is not None else None


def boleh(user, komponen: str, aksi: str, obj=None) -> bool:
    """Apakah `user` boleh melakukan `aksi` pada `komponen` (dan `obj`)?

    Contoh:
        boleh(request.user, "matriks", "tambah")
        boleh(request.user, "verifikasi", "jawab", log)
    """
    if not user.is_authenticated:
        return False
    if aksi == "lihat":
        return True
    if user.is_superuser:
        return True

    kebijakan = KEBIJAKAN[komponen]

    # Peran "sunting" boleh semua aksi.
    if user.peran in kebijakan["sunting"]:
        return True

    # Peran terbatas pada OPD sendiri.
    aksi_opd = kebijakan["opd"].get(user.peran, set())
    if aksi not in aksi_opd or not user.opd_id:
        return False
    if obj is None:          # mis. tombol "Tambah": cukup punya OPD
        return True
    return _opd_id(obj) == user.opd_id


def label_hak(user, komponen: str) -> str:
    """Teks ringkas hak akses pengguna untuk ditampilkan di UI."""
    kebijakan = KEBIJAKAN[komponen]
    if user.is_superuser or user.peran in kebijakan["sunting"]:
        return "Sunting"
    if kebijakan["opd"].get(user.peran):
        return "Sunting terbatas"
    return "Lihat"


def batasi_opd(user, queryset, jalur: str = "opd"):
    """Membatasi queryset agar PIC hanya melihat data OPD-nya sendiri.

    `jalur` = nama relasi menuju OPD, mis. "opd" atau "butir__opd".
    Peran lain tidak dibatasi.
    """
    if user.is_authenticated and user.peran == PERAN_PIC and not user.is_superuser:
        if not user.opd_id:
            return queryset.none()
        return queryset.filter(**{f"{jalur}_id": user.opd_id})
    return queryset
