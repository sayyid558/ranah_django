"""Pendaftaran model `accounts` ke panel admin Django (/admin/)."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Opd, User


@admin.register(Opd)
class OpdAdmin(admin.ModelAdmin):
    list_display = ("nama", "singkatan", "sektor")
    search_fields = ("nama", "singkatan")


@admin.register(User)
class PenggunaAdmin(UserAdmin):
    """Menambahkan kolom peran/OPD ke form admin pengguna bawaan."""

    list_display = ("username", "get_full_name", "peran", "opd", "is_active")
    list_filter = ("peran", "opd", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("Peran RANAH", {"fields": ("peran", "opd", "telepon")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Peran RANAH", {"fields": ("first_name", "last_name", "email", "peran", "opd", "telepon")}),
    )
