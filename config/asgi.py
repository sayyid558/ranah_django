"""
ASGI entry point - dipakai server asinkron (uvicorn, daphne) bila diperlukan.
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_asgi_application()
