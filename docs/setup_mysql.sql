-- ============================================================
-- Skrip penyiapan database MySQL untuk RANAH
-- Jalankan:  mysql -u root -p < docs/setup_mysql.sql
-- ============================================================

-- utf8mb4 agar seluruh karakter (termasuk emoji) tersimpan dengan benar
CREATE DATABASE IF NOT EXISTS ranah_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- Pengguna khusus aplikasi (jangan pakai root di aplikasi!)
-- GANTI kata sandi ini, lalu samakan dengan DB_PASSWORD di file .env
CREATE USER IF NOT EXISTS 'ranah_user'@'localhost' IDENTIFIED BY '';

-- Beri hak penuh hanya pada database ranah_db
GRANT ALL PRIVILEGES ON ranah_db.* TO 'ranah_user'@'localhost';
FLUSH PRIVILEGES;
