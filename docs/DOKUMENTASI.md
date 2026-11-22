# Dokumentasi Kode RANAH

Panduan belajar: dari gambaran besar, alur kerja Django, sampai penjelasan **setiap file**.
Cocok dibaca sambil membuka kodenya.

## Daftar Isi
1. [Gambaran besar](#1-gambaran-besar)
2. [Konsep Django yang dipakai](#2-konsep-django-yang-dipakai)
3. [Alur satu permintaan (request)](#3-alur-satu-permintaan-request)
4. [Penjelasan per file](#4-penjelasan-per-file)
5. [Model data & relasi](#5-model-data--relasi)
6. [Sistem hak akses](#6-sistem-hak-akses)
7. [Rumus indikator H1–H3 & P1–P3](#7-rumus-indikator)
8. [Resep modifikasi](#8-resep-modifikasi)
9. [Catatan produksi](#9-catatan-produksi)

---

## 1. Gambaran besar

```
Browser ──► config/urls.py ──► workspace/urls.py ──► workspace/views.py
                                                        │  │
                              accounts/permissions.py ◄─┘  ├─► workspace/forms.py
                              (boleh/tidak?)               ├─► workspace/models.py ◄──► MySQL
                                                           └─► templates/*.html (+ static/css)
```

Proyek terdiri dari dua **app** Django:

| App | Tanggung jawab |
|-----|----------------|
| `accounts` | Pengguna (dengan **peran**), OPD/instansi, dan aturan hak akses |
| `workspace` | Enam komponen ruang kerja (model, form, view, URL, perhitungan indikator) |

## 2. Konsep Django yang dipakai

| Konsep | Arti singkat | Contoh di proyek |
|--------|--------------|------------------|
| **Model** | Kelas Python = tabel database | `ButirData` di `workspace/models.py` |
| **Migration** | Riwayat perubahan skema tabel | `makemigrations` + `migrate` |
| **View** | Fungsi/kelas yang menjawab permintaan | `MatriksDaftar` di `views.py` |
| **Template** | HTML dengan tag `{% %}` dan `{{ }}` | `templates/crud/daftar.html` |
| **URLconf** | Peta alamat URL → view | `workspace/urls.py` |
| **ModelForm** | Form otomatis dari model + validasi | `ButirDataForm` di `forms.py` |
| **Mixin** | Potongan perilaku yang bisa digabung | `KomponenMixin`, `PesanMixin` |
| **Management command** | Perintah `manage.py` buatan sendiri | `seed_demo`, `kirim_pengingat` |
| **Context processor** | Menyuntikkan data ke semua template | `context_processors.navigasi` |

## 3. Alur satu permintaan (request)

Contoh: PIC membuka **Matriks Kebutuhan Data** (`/matriks/`).

1. `config/urls.py` meneruskan `""` ke `workspace/urls.py`.
2. `workspace/urls.py` cocok dengan `matriks/` → `MatriksDaftar`.
3. `LoginRequiredMixin` memeriksa login; tamu dialihkan ke `/masuk/`.
4. `DaftarView.get_queryset()` mengambil data, **membatasi ke OPD si PIC** (`batasi_opd`), lalu menerapkan pencarian/filter dari `?q=`, `?status=`, dll.
5. `DaftarView.get_context_data()` menyusun baris tabel dan tombol Ubah/Hapus sesuai `boleh()`.
6. Template `crud/daftar.html` (turunan `base.html`) dirender dan dikirim ke browser.

Alur **tambah/ubah**: GET menampilkan form → POST divalidasi `ModelForm` → `form_valid()` menyimpan → pesan sukses → redirect ke daftar.

## 4. Penjelasan per file

### Akar proyek
| File | Fungsi |
|------|--------|
| `manage.py` | Pintu masuk semua perintah (`runserver`, `migrate`, …). |
| `requirements.txt` | Daftar paket: Django, PyMySQL, cryptography. |
| `.env.example` | Contoh konfigurasi (kunci rahasia, database, email). Salin jadi `.env`. |
| `.gitignore` | Berkas yang tidak ikut Git (`.env`, `venv/`, unggahan). |

### `config/` — konfigurasi proyek
| File | Penjelasan |
|------|------------|
| `__init__.py` | Mengaktifkan **PyMySQL** sebagai driver MySQL agar tak perlu compiler C. |
| `settings.py` | Pengaturan utama. Fitur penting: pembaca `.env` buatan sendiri; pilihan database `mysql`/`sqlite` lewat `DB_ENGINE`; `AUTH_USER_MODEL = "accounts.User"`; bahasa `id` & zona `Asia/Jakarta`; konfigurasi email; context processor menu. |
| `urls.py` | `/admin/`, `/masuk/`, `/keluar/`, lalu semua sisanya ke `workspace.urls`. |
| `wsgi.py`, `asgi.py` | Titik masuk server produksi. |

### `accounts/` — pengguna & hak akses
| File | Penjelasan |
|------|------------|
| `models.py` | `Opd` (instansi) dan `User` (turunan `AbstractUser` + `peran` + `opd` + `telepon`). Konstanta peran (`PERAN_TEKNIS`, …) berupa string biasa. |
| `permissions.py` | **Jantung hak akses.** `KEBIJAKAN` (tabel aturan), `boleh(user, komponen, aksi, obj)`, `label_hak()`, `batasi_opd()`. |
| `admin.py` | Menampilkan peran/OPD di panel admin pengguna. |
| `apps.py` | Konfigurasi app. |

### `workspace/` — enam komponen
| File | Penjelasan |
|------|------------|
| `models.py` | Semua tabel (lihat [bagian 5](#5-model-data--relasi)). Memuat logika bisnis di `save()` dan properti turunan. |
| `forms.py` | `ModelForm` tiap komponen + `GayaMixin` (menambah class CSS). `ButirDataForm` menyembunyikan kolom OPD/PIC/status bagi PIC. |
| `views.py` | Kelas dasar generik (A) + dashboard (B) + tiap komponen (C–H). Dibaca berurutan dari atas. |
| `urls.py` | Peta URL; nama `<komponen>_<aksi>` dipakai di template. |
| `indikator.py` | Rumus otomatis H1–H3, P1–P3 + metadata (`DAFTAR_INDIKATOR`). |
| `context_processors.py` | Menyediakan `menu` sidebar; berisi daftar `KOMPONEN`. |
| `ikon.py`, `templatetags/ranah_tags.py` | Ikon SVG + tag `{% ikon "nama" %}`. |
| `admin.py` | Mendaftarkan model ke `/admin/`. |
| `management/commands/seed_demo.py` | Mengisi data contoh (OPD, akun, butir, log, agenda, dokumen, target). |
| `management/commands/kirim_pengingat.py` | Email pengingat otomatis ke PIC. |

#### Mengenal `views.py` lebih dalam
- **`KomponenMixin`** — atribut `komponen`, `prefix`, `judul`, `url_sukses`; menyuntikkan konteks umum & menentukan redirect.
- **`DaftarView`** — tabel generik. Cukup isi `kolom`, `cari`, `filter_status`, `relasi`, `aksi_baris`. Kolom bertipe `"badge"` tampil sebagai lencana berwarna; `"relasi.atribut"` menelusuri relasi.
- **`TambahView` / `UbahView` / `HapusView`** — CRUD generik dengan cek izin. `UbahView.aksi_ubah` memungkinkan form khusus (PIC `jawab`, `perbarui_status`).
- **Pola konfigurasi bersama** (`MatriksCfg`, `VerifikasiCfg`, …) — kelas kecil berisi atribut yang dicampur (multiple inheritance) ke view-view komponen agar tidak mengulang.
- **`KalenderView`** — membangun grid bulan dengan modul `calendar`, menggabungkan `Agenda` dengan jumlah batas waktu data per tanggal.
- **`PustakaUnduh`** — unduhan lewat view (wajib login), tidak membuka folder `media/` ke publik.

### `templates/`
| File | Penjelasan |
|------|------------|
| `base.html` | Kerangka: sidebar (loop `menu`), topbar, pesan. Template lain `extends` ini. |
| `registration/login.html` | Halaman login dua kolom (dipakai `LoginView` bawaan). |
| `crud/daftar.html` | Tabel generik + filter + paginasi. |
| `crud/form.html` | Form generik; merender field satu per satu, mendukung unggah berkas. |
| `crud/hapus.html` | Konfirmasi hapus. |
| `workspace/dashboard.html` | Beranda: sambutan, angka ringkas, 6 kartu, agenda, indikator. |
| `workspace/kalender.html` | Kalender bulanan + daftar agenda. |
| `workspace/pustaka.html` | Galeri dokumen + chip kategori. |
| `workspace/indikator.html` | Kartu triwulan + matriks tahunan. |
| `workspace/indikator_target.html` | Form target 6 indikator × 4 triwulan. |

> Aturan template: `{% extends %}` harus tag **pertama** di berkas.

### `static/`
- `css/ranah.css` — tema oranye. Warna diatur lewat variabel `--o-50 … --o-900` di bagian atas; ubah di sana untuk mengganti warna seluruh aplikasi.
- `js/ranah.js` — sidebar mobile, pesan hilang otomatis, dialog konfirmasi (`data-konfirmasi`).

## 5. Model data & relasi

```
Opd ──< User (peran, opd)
Opd ──< ButirData >── User (pic)          [Komponen 1]
ButirData ──< LogVerifikasi               [Komponen 2]
Opd ──< TindakLanjut >── Agenda           [Komponen 3, 4]
Dokumen                                    [Komponen 5]
TargetIndikator (kode, tahun, triwulan)    [Komponen 6]
```

**Logika otomatis di model (penting dipahami):**

| Lokasi | Perilaku |
|--------|----------|
| `ButirData.save()` | Mengisi `tanggal_diterima` dan status masih "belum" → status menjadi "diterima". |
| `LogVerifikasi.save()` | (1) `perlu_permintaan_ulang` = ada pemeriksaan yang tidak sesuai; (2) catat waktu jawaban; (3) bila log terbaru → **status butir otomatis** "terverifikasi"/"revisi". |
| `TindakLanjut.save()` | `tanggal_selesai` terisi saat status "selesai", terhapus jika dibuka kembali. |
| `ButirData.jumlah_permintaan_ulang` | Dihitung dari log (properti, tidak disimpan). |

## 6. Sistem hak akses

Seluruh aturan ada di **satu tempat**: dictionary `KEBIJAKAN` di `accounts/permissions.py`.

```python
"matriks": {
    "sunting": {PERAN_TEKNIS},                  # boleh semua aksi
    "opd": {PERAN_PIC: {"tambah", "ubah"}},     # PIC: hanya baris OPD sendiri
},
```

- `boleh(user, "matriks", "ubah", obj)` dipakai di view (menolak dengan 403) dan saat menyusun tombol di tabel.
- `batasi_opd(user, queryset, "opd")` menyaring data agar PIC hanya melihat OPD-nya (juga mencegah mengakses URL baris lain → 404).
- Superuser selalu boleh.
- Kini menambah aturan = menambah satu baris di `KEBIJAKAN`.

## 7. Rumus indikator

Terdapat di `workspace/indikator.py`. **Definisi di bawah adalah asumsi**; sesuaikan dengan Tabel 3.7 Anda.

| Kode | Nama | Rumus | Arah |
|------|------|-------|------|
| H1 | Ketepatan waktu penerimaan data | butir diterima ≤ batas ÷ butir jatuh tempo/diterima × 100 | ↑ |
| H2 | Kelengkapan & kesesuaian data | butir terverifikasi ÷ butir diterima × 100 | ↑ |
| H3 | Penyelesaian tindak lanjut forum | tindak lanjut selesai ÷ total × 100 | ↑ |
| P1 | Permintaan ulang per butir | jumlah log perlu-ulang ÷ butir diterima | ↓ |
| P2 | Keterlambatan penerimaan data | rata-rata hari terlambat (tepat waktu = 0) | ↓ |
| P3 | Tindak lanjut selesai tepat waktu | selesai ≤ batas ÷ total × 100 | ↑ |

Cara mengubah: edit fungsi `h1…p3` (rumus) atau entri di `DAFTAR_INDIKATOR` (nama, satuan, arah). Dashboard, kartu, dan tabel rekap menyesuaikan otomatis.

## 8. Resep modifikasi

**Menambah kolom pada butir data** (mis. `keterangan`)
1. Tambahkan field di `ButirData` (`models.py`).
2. Tambahkan nama field ke `fields` di `ButirDataForm` (`forms.py`).
3. (Opsional) tambah tuple di `MatriksDaftar.kolom` (`views.py`).
4. `python manage.py makemigrations` lalu `migrate`.

**Menambah peran baru**
1. Tambah konstanta & pilihan di `accounts/models.py`.
2. Masukkan ke himpunan yang sesuai di `KEBIJAKAN`.
3. `makemigrations` + `migrate` (pilihan `choices` berubah).

**Menambah komponen ke-7**
1. Model + form di `workspace/`.
2. Tambah `Cfg`, `Daftar`, `Tambah`, `Ubah`, `Hapus` di `views.py` (salin pola komponen 3).
3. Daftarkan 4 URL di `urls.py` dengan pola `<nama>_daftar|tambah|ubah|hapus`.
4. Tambahkan ke `KEBIJAKAN` dan daftar `KOMPONEN` (menu otomatis muncul).

**Mengganti warna tema** — ubah `--o-500` dan kawan-kawannya di `static/css/ranah.css`.

**Mengubah batas ukuran unggahan** — `UKURAN_MAKS_UNGGAHAN_MB` di `settings.py`; ekstensi diizinkan ada di `Dokumen.berkas` (`models.py`).

## 9. Catatan produksi
- Set `DJANGO_DEBUG=False`, ganti `DJANGO_SECRET_KEY`, isi `DJANGO_ALLOWED_HOSTS`.
- `python manage.py collectstatic`, layani `/static/` lewat Nginx (atau pasang WhiteNoise).
- Jalankan dengan `gunicorn config.wsgi:application` di belakang Nginx + HTTPS.
- Ganti seluruh kata sandi akun demo; cadangkan database MySQL secara berkala.
- Jadwalkan `kirim_pengingat` dengan cron.
- Folder `media/` berisi unggahan; cadangkan juga dan jangan diekspos langsung.
