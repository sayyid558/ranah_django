#!/usr/bin/env python
"""
manage.py - pintu masuk perintah administratif Django.

Contoh perintah yang sering dipakai:
    python manage.py runserver          -> menjalankan server pengembangan
    python manage.py makemigrations     -> membuat berkas migrasi dari models.py
    python manage.py migrate            -> menerapkan migrasi ke database
    python manage.py createsuperuser    -> membuat akun admin
    python manage.py seed_demo          -> mengisi data contoh RANAH
"""
import os
import sys


def main():
    # Memberi tahu Django modul pengaturan mana yang dipakai.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django belum terpasang. Jalankan: pip install -r requirements.txt"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
