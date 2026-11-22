/**
 * ranah.js - JavaScript ringan untuk antarmuka RANAH.
 * Tanpa library eksternal. Fungsi:
 *   1. Membuka/menutup sidebar di layar kecil.
 *   2. Menghilangkan pesan (toast) otomatis setelah 5 detik.
 *   3. Meminta konfirmasi pada tombol/ formulir yang bertanda data-konfirmasi.
 */
document.addEventListener("DOMContentLoaded", function () {
  // 1. Sidebar mobile
  var tombol = document.getElementById("btn-menu");
  var sidebar = document.getElementById("sidebar");
  if (tombol && sidebar) {
    tombol.addEventListener("click", function () {
      sidebar.classList.toggle("buka");
    });
    // Klik di luar sidebar menutupnya
    document.addEventListener("click", function (e) {
      if (!sidebar.contains(e.target) && !tombol.contains(e.target)) {
        sidebar.classList.remove("buka");
      }
    });
  }

  // 2. Pesan hilang otomatis
  document.querySelectorAll(".pesan").forEach(function (el) {
    setTimeout(function () {
      el.style.transition = "opacity .5s";
      el.style.opacity = "0";
      setTimeout(function () { el.remove(); }, 500);
    }, 5000);
  });

  // 3. Konfirmasi: <form data-konfirmasi="Yakin?">
  document.querySelectorAll("[data-konfirmasi]").forEach(function (el) {
    el.addEventListener("submit", function (e) {
      if (!window.confirm(el.getAttribute("data-konfirmasi"))) e.preventDefault();
    });
  });
});
