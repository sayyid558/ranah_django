"""Pendaftaran model komponen RANAH ke panel admin Django (/admin/)."""
from django.contrib import admin

from .models import Agenda, ButirData, Dokumen, LogVerifikasi, TargetIndikator, TindakLanjut


@admin.register(ButirData)
class ButirDataAdmin(admin.ModelAdmin):
    list_display = ("kode", "jenis_data", "opd", "tahun", "triwulan", "batas_waktu", "tanggal_diterima", "status")
    list_filter = ("tahun", "triwulan", "status", "opd")
    search_fields = ("kode", "jenis_data")


@admin.register(LogVerifikasi)
class LogVerifikasiAdmin(admin.ModelAdmin):
    list_display = ("butir", "tanggal", "perlu_permintaan_ulang", "diverifikasi_oleh")
    list_filter = ("perlu_permintaan_ulang",)


@admin.register(TindakLanjut)
class TindakLanjutAdmin(admin.ModelAdmin):
    list_display = ("isu", "opd", "penanggung_jawab", "batas_waktu", "status")
    list_filter = ("status", "tahun", "triwulan")


@admin.register(Agenda)
class AgendaAdmin(admin.ModelAdmin):
    list_display = ("judul", "jenis", "tanggal", "jam")
    list_filter = ("jenis",)


@admin.register(Dokumen)
class DokumenAdmin(admin.ModelAdmin):
    list_display = ("judul", "kategori", "diunggah_oleh", "dibuat")
    list_filter = ("kategori",)


@admin.register(TargetIndikator)
class TargetIndikatorAdmin(admin.ModelAdmin):
    list_display = ("kode", "tahun", "triwulan", "target")
    list_filter = ("tahun", "kode")
