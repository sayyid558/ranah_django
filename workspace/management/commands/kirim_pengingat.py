"""
Perintah:  python manage.py kirim_pengingat

Pengingat OTOMATIS kepada PIC (Komponen 4):
  1. Butir data yang BELUM diterima dan batas waktunya <= N hari lagi
     (atau sudah lewat)  -> dikirim ke PIC butir tersebut.
  2. Agenda yang jatuh pada (hari ini + pengingat_hari)  -> dikirim ke SEMUA PIC.

Opsi:
    --hari 3       jendela peringatan batas data (default 3 hari)
    --dry-run      hanya tampilkan, tidak mengirim email

Jadwalkan harian dengan cron (Linux), contoh tiap hari 07.00:
    0 7 * * *  cd /path/ke/ranah && /path/ke/venv/bin/python manage.py kirim_pengingat

Di Windows gunakan Task Scheduler dengan perintah yang sama.
"""
from collections import defaultdict
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import PERAN_PIC, User
from workspace.models import Agenda, ButirData


class Command(BaseCommand):
    help = "Mengirim email pengingat batas waktu data dan agenda kepada PIC."

    def add_arguments(self, parser):
        parser.add_argument("--hari", type=int, default=3, help="Jendela peringatan batas data (hari).")
        parser.add_argument("--dry-run", action="store_true", help="Tampilkan saja, jangan kirim email.")

    def _kirim(self, penerima, subjek, isi, dry):
        """Mengirim satu email (atau mencetaknya saat --dry-run)."""
        if not penerima:
            return 0
        if dry:
            self.stdout.write(f"[DRY-RUN] ke {', '.join(penerima)} | {subjek}")
            return 1
        send_mail(subjek, isi, settings.DEFAULT_FROM_EMAIL, penerima, fail_silently=False)
        return 1

    def handle(self, *args, **opsi):
        hari = timezone.localdate()
        batas_peringatan = hari + timedelta(days=opsi["hari"])
        dry = opsi["dry_run"]
        terkirim = 0

        # --- 1. Pengingat batas waktu data per PIC ------------------------
        per_pic = defaultdict(list)
        belum = ButirData.objects.filter(
            tanggal_diterima__isnull=True, batas_waktu__lte=batas_peringatan, pic__isnull=False
        ).select_related("pic", "opd")
        for b in belum:
            per_pic[b.pic].append(b)

        for pic, daftar in per_pic.items():
            if not pic.email:
                continue
            baris = [
                f"- {b.kode} {b.jenis_data} (batas {b.batas_waktu:%d-%m-%Y}"
                f"{', TERLAMBAT' if b.batas_waktu < hari else ''})"
                for b in daftar
            ]
            isi = (
                f"Yth. {pic.nama_tampil},\n\n"
                "Berikut butir data yang belum kami terima dan mendekati/melewati batas waktu:\n\n"
                + "\n".join(baris)
                + "\n\nMohon segera dikirimkan. Terima kasih.\n\nRANAH - Ruang Kerja Digital"
            )
            terkirim += self._kirim([pic.email], "[RANAH] Pengingat batas waktu data", isi, dry)

        # --- 2. Pengingat agenda ke seluruh PIC --------------------------
        email_pic = list(
            User.objects.filter(peran=PERAN_PIC, is_active=True).exclude(email="").values_list("email", flat=True)
        )
        for a in Agenda.objects.filter(tanggal__gte=hari):
            if a.tanggal - hari == timedelta(days=a.pengingat_hari):
                jam = f" pukul {a.jam:%H:%M}" if a.jam else ""
                isi = (
                    f"Pengingat agenda: {a.judul}\n"
                    f"Tanggal: {a.tanggal:%d-%m-%Y}{jam}\n"
                    f"Lokasi: {a.lokasi or '-'}\n\n{a.deskripsi}\n\nRANAH - Ruang Kerja Digital"
                )
                terkirim += self._kirim(email_pic, f"[RANAH] Pengingat: {a.judul}", isi, dry)

        self.stdout.write(self.style.SUCCESS(f"Selesai. {terkirim} email {'disimulasikan' if dry else 'dikirim'}."))
