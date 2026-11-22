"""
Pengaturan (settings) proyek RANAH - Ruang Kerja Digital.

Semua nilai sensitif (kunci rahasia, kata sandi database) dibaca dari
variabel lingkungan / berkas `.env` sehingga tidak tertulis di dalam kode.
Dokumentasi resmi: https://docs.djangoproject.com/en/stable/ref/settings/
"""
import os
from pathlib import Path

# Folder induk proyek (yang berisi manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# 1. Pembaca berkas .env sederhana (tanpa paket tambahan)
# ---------------------------------------------------------------------------
def _muat_env(path: Path) -> None:
    """Membaca baris KUNCI=NILAI dari berkas .env ke os.environ.

    Baris kosong dan baris berawalan '#' diabaikan. Variabel yang sudah
    ada di lingkungan sistem tidak ditimpa (setdefault).
    """
    if not path.exists():
        return
    for baris in path.read_text(encoding="utf-8").splitlines():
        baris = baris.strip()
        if not baris or baris.startswith("#") or "=" not in baris:
            continue
        kunci, nilai = baris.split("=", 1)
        os.environ.setdefault(kunci.strip(), nilai.strip().strip('"').strip("'"))


_muat_env(BASE_DIR / ".env")


def _env_bool(nama: str, default: bool = False) -> bool:
    """Mengubah variabel lingkungan menjadi True/False."""
    return os.environ.get(nama, str(default)).strip().lower() in ("1", "true", "yes", "ya")


# ---------------------------------------------------------------------------
# 2. Keamanan dasar
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "kunci-pengembangan-jangan-dipakai-di-produksi")
DEBUG = _env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]


# ---------------------------------------------------------------------------
# 3. Aplikasi yang aktif
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # --- Aplikasi RANAH ---
    "accounts",   # pengguna, peran, dan OPD/instansi
    "workspace",  # 6 komponen ruang kerja digital
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ---------------------------------------------------------------------------
# 4. Template (HTML)
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # folder templates global
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Menyediakan menu sidebar ke semua template:
                "workspace.context_processors.navigasi",
            ],
        },
    },
]


# ---------------------------------------------------------------------------
# 5. Database - MySQL (default) atau SQLite (uji cepat)
# ---------------------------------------------------------------------------
DB_ENGINE = os.environ.get("DB_ENGINE", "mysql").strip().lower()

if DB_ENGINE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ.get("DB_NAME", "ranah_db"),
            "USER": os.environ.get("DB_USER", "root"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("DB_PORT", "3306"),
            "OPTIONS": {
                # utf8mb4 mendukung seluruh karakter Unicode (termasuk emoji)
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------------------------------------------------------
# 6. Autentikasi
# ---------------------------------------------------------------------------
# Model pengguna kustom (punya kolom peran & OPD) - lihat accounts/models.py
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"


# ---------------------------------------------------------------------------
# 7. Bahasa, zona waktu
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "id"          # antarmuka & format tanggal bahasa Indonesia
TIME_ZONE = "Asia/Jakarta"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# 8. Berkas statis & unggahan
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]   # CSS/JS buatan kita
STATIC_ROOT = BASE_DIR / "staticfiles"     # tujuan `collectstatic` (produksi)

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"            # lokasi berkas Pustaka Dokumen
# Batas ukuran unggahan Pustaka Dokumen (MB) - dipakai di workspace/models.py
UKURAN_MAKS_UNGGAHAN_MB = 15


# ---------------------------------------------------------------------------
# 9. Email (untuk pengingat otomatis)
# ---------------------------------------------------------------------------
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "25"))
EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", False)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "ranah@localhost")
