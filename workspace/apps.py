"""Konfigurasi aplikasi `workspace` (6 komponen RANAH)."""
from django.apps import AppConfig


class WorkspaceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "workspace"
    verbose_name = "Ruang Kerja RANAH"
