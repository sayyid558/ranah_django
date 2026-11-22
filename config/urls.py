"""
Routing URL utama proyek.

Urutan:
  /admin/    -> panel admin bawaan Django
  /masuk/    -> halaman login   (nama URL: "login")
  /keluar/   -> logout          (nama URL: "logout")
  /          -> diteruskan ke workspace/urls.py (dashboard & 6 komponen)
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # LoginView bawaan Django memakai templates/registration/login.html
    path("masuk/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    # Logout harus lewat POST (aman dari CSRF) - tombolnya ada di sidebar
    path("keluar/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("workspace.urls")),
]
