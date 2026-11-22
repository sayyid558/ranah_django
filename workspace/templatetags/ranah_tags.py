"""
Tag template kustom RANAH.

Pemakaian di template:
    {% load ranah_tags %}
    {% ikon "kalender" %}
    {% ikon "tambah" 18 %}      <- ukuran piksel opsional
"""
from django import template
from django.utils.safestring import mark_safe

from workspace.ikon import IKON

register = template.Library()


@register.simple_tag
def ikon(nama: str, ukuran: int = 20):
    """Menghasilkan elemen <svg> untuk ikon bernama `nama`."""
    isi = IKON.get(nama, "")
    return mark_safe(
        f'<svg class="ikon" width="{ukuran}" height="{ukuran}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{isi}</svg>'
    )
