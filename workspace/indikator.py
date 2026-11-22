"""
Perhitungan otomatis Rekap Indikator (Komponen 6).

Komponen 6 pada rancangan RANAH berisi "rumus otomatis yang menghitung
H1-H3 dan P1-P3 dari komponen 1-3 tiap triwulan". File ini adalah
rumus-rumus itu.

PENTING - SESUAIKAN DENGAN TABEL 3.7:
  Definisi tiap indikator di bawah adalah ASUMSI yang masuk akal karena
  isi Tabel 3.7 tidak tersedia saat aplikasi dibuat. Untuk mengubahnya,
  edit fungsi hitung (h1..p3) atau teks `nama`/`keterangan` pada daftar
  DAFTAR_INDIKATOR - bagian lain aplikasi menyesuaikan otomatis.

  H = indikator Hasil (kualitas data), P = indikator Proses (kelancaran kerja).

Arah penilaian:
  "naik"  -> makin besar makin baik (target tercapai bila nilai >= target)
  "turun" -> makin kecil makin baik (target tercapai bila nilai <= target)
"""
from dataclasses import dataclass
from typing import Callable, Optional

from django.db.models import F, Q
from django.utils import timezone

from .models import (
    ButirData, LogVerifikasi, TindakLanjut, TargetIndikator,
    STATUS_BELUM, STATUS_TERVERIFIKASI, TL_SELESAI,
)


def _persen(pembilang: int, penyebut: int) -> Optional[float]:
    """Persentase 1 desimal; None bila penyebut 0 (belum ada data)."""
    return round(pembilang * 100 / penyebut, 1) if penyebut else None


# ---------------------------------------------------------------------------
# Rumus indikator. Semua menerima (tahun, triwulan) dan mengembalikan angka
# atau None bila belum ada data untuk dihitung.
# ---------------------------------------------------------------------------
def h1(tahun: int, tw: int) -> Optional[float]:
    """H1 - Ketepatan waktu penerimaan data (%).  [Komponen 1]

    = butir diterima tepat waktu / (butir sudah diterima + butir belum
      diterima yang batas waktunya sudah lewat)
    """
    qs = ButirData.objects.filter(tahun=tahun, triwulan=tw)
    jatuh_tempo = qs.filter(Q(tanggal_diterima__isnull=False) | Q(batas_waktu__lt=timezone.localdate())).count()
    tepat = qs.filter(tanggal_diterima__isnull=False, tanggal_diterima__lte=F("batas_waktu")).count()
    return _persen(tepat, jatuh_tempo)


def h2(tahun: int, tw: int) -> Optional[float]:
    """H2 - Kelengkapan & kesesuaian data (%).  [Komponen 1-2]

    = butir berstatus Terverifikasi / butir yang sudah diterima
    """
    diterima = ButirData.objects.filter(tahun=tahun, triwulan=tw).exclude(status=STATUS_BELUM)
    return _persen(diterima.filter(status=STATUS_TERVERIFIKASI).count(), diterima.count())


def h3(tahun: int, tw: int) -> Optional[float]:
    """H3 - Tindak lanjut forum yang terselesaikan (%).  [Komponen 3]"""
    qs = TindakLanjut.objects.filter(tahun=tahun, triwulan=tw)
    return _persen(qs.filter(status=TL_SELESAI).count(), qs.count())


def p1(tahun: int, tw: int) -> Optional[float]:
    """P1 - Rata-rata permintaan ulang per butir data (kali).  [Komponen 2]

    Makin kecil makin baik: artinya data jarang harus diminta ulang.
    """
    diterima = ButirData.objects.filter(tahun=tahun, triwulan=tw).exclude(status=STATUS_BELUM).count()
    if not diterima:
        return None
    ulang = LogVerifikasi.objects.filter(butir__tahun=tahun, butir__triwulan=tw, perlu_permintaan_ulang=True).count()
    return round(ulang / diterima, 2)


def p2(tahun: int, tw: int) -> Optional[float]:
    """P2 - Rata-rata keterlambatan penerimaan data (hari).  [Komponen 1]

    Butir yang tepat waktu dihitung 0 hari.
    """
    pasangan = ButirData.objects.filter(
        tahun=tahun, triwulan=tw, tanggal_diterima__isnull=False
    ).values_list("tanggal_diterima", "batas_waktu")
    selisih = [max(0, (diterima - batas).days) for diterima, batas in pasangan]
    return round(sum(selisih) / len(selisih), 1) if selisih else None


def p3(tahun: int, tw: int) -> Optional[float]:
    """P3 - Tindak lanjut forum yang selesai tepat waktu (%).  [Komponen 3]"""
    qs = TindakLanjut.objects.filter(tahun=tahun, triwulan=tw)
    tepat = qs.filter(status=TL_SELESAI, tanggal_selesai__lte=F("batas_waktu")).count()
    return _persen(tepat, qs.count())


# ---------------------------------------------------------------------------
# Metadata indikator
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Indikator:
    kode: str
    nama: str
    keterangan: str
    satuan: str
    arah: str                                   # "naik" | "turun"
    hitung: Callable[[int, int], Optional[float]]
    sumber: str                                 # asal data, ditampilkan di UI


DAFTAR_INDIKATOR = [
    Indikator("H1", "Ketepatan waktu penerimaan data", "Butir data diterima sebelum/pada batas waktu.", "%", "naik", h1, "Komponen 1"),
    Indikator("H2", "Kelengkapan & kesesuaian data", "Butir data lolos verifikasi (lengkap, periode, cakupan, satuan).", "%", "naik", h2, "Komponen 1-2"),
    Indikator("H3", "Penyelesaian tindak lanjut forum", "Tindak lanjut forum berstatus selesai.", "%", "naik", h3, "Komponen 3"),
    Indikator("P1", "Permintaan ulang per butir data", "Rata-rata berapa kali satu butir data diminta ulang.", "kali", "turun", p1, "Komponen 2"),
    Indikator("P2", "Keterlambatan penerimaan data", "Rata-rata hari keterlambatan penerimaan data.", "hari", "turun", p2, "Komponen 1"),
    Indikator("P3", "Tindak lanjut selesai tepat waktu", "Tindak lanjut selesai sebelum/pada batas waktunya.", "%", "naik", p3, "Komponen 3"),
]


def ambil_target(tahun: int) -> dict:
    """Mengembalikan {(kode, triwulan): target_float} untuk satu tahun."""
    return {(t.kode, t.triwulan): float(t.target) for t in TargetIndikator.objects.filter(tahun=tahun)}


def _tercapai(ind: Indikator, nilai: Optional[float], target: Optional[float]) -> Optional[bool]:
    """True/False bila bisa dinilai, None bila nilai atau target belum ada."""
    if nilai is None or target is None:
        return None
    return nilai >= target if ind.arah == "naik" else nilai <= target


def hitung_triwulan(tahun: int, tw: int, target: Optional[dict] = None) -> list:
    """Hasil keenam indikator untuk satu triwulan (dipakai dashboard)."""
    target = target if target is not None else ambil_target(tahun)
    hasil = []
    for ind in DAFTAR_INDIKATOR:
        nilai = ind.hitung(tahun, tw)
        t = target.get((ind.kode, tw))
        hasil.append({"indikator": ind, "nilai": nilai, "target": t, "tercapai": _tercapai(ind, nilai, t)})
    return hasil


def rekap_tahunan(tahun: int) -> list:
    """Matriks indikator x 4 triwulan untuk halaman Rekap Indikator."""
    target = ambil_target(tahun)
    per_tw = {tw: hitung_triwulan(tahun, tw, target) for tw in (1, 2, 3, 4)}
    baris = []
    for i, ind in enumerate(DAFTAR_INDIKATOR):
        baris.append({"indikator": ind, "sel": [per_tw[tw][i] | {"triwulan": tw} for tw in (1, 2, 3, 4)]})
    return baris
