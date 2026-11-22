"""
Context processor: menyuntikkan data ke SEMUA template.

Di sini kita menyediakan `menu` (daftar navigasi sidebar) beserta label hak
akses pengguna pada tiap komponen. Didaftarkan di settings.TEMPLATES.
"""
from accounts.permissions import label_hak

# (kunci komponen, nomor, judul, nama URL, nama ikon, deskripsi singkat)
KOMPONEN = [
    ("matriks", 1, "Matriks Kebutuhan Data dan Jadwal", "matriks_daftar", "matriks",
     "Daftar butir data, OPD, PIC, batas waktu, dan status penerimaan."),
    ("verifikasi", 2, "Log Verifikasi dan Permintaan Ulang", "verifikasi_daftar", "verifikasi",
     "Hasil pemeriksaan data dan klarifikasi dengan OPD/instansi."),
    ("tindaklanjut", 3, "Matriks Tindak Lanjut Forum", "tindaklanjut_daftar", "tindaklanjut",
     "Isu forum, penanggung jawab, batas waktu, dan status."),
    ("kalender", 4, "Kalender Koordinasi dan Pengingat", "kalender", "kalender",
     "Jadwal forum, batas waktu data, dan pengingat otomatis."),
    ("pustaka", 5, "Pustaka Dokumen", "pustaka", "pustaka",
     "SOP, format, panduan, notulen, dan bahan forum/analisis."),
    ("indikator", 6, "Rekap Indikator", "indikator", "indikator",
     "Capaian indikator H1-H3 dan P1-P3 per triwulan."),
]


def navigasi(request):
    """Mengembalikan {'menu': [...]} untuk sidebar; kosong bila belum login."""
    if not request.user.is_authenticated:
        return {}
    menu = [
        {
            "kunci": kunci, "nomor": nomor, "judul": judul, "url": url_name,
            "ikon": ikon, "deskripsi": deskripsi,
            "hak": label_hak(request.user, kunci),
        }
        for kunci, nomor, judul, url_name, ikon, deskripsi in KOMPONEN
    ]
    return {"menu": menu}
