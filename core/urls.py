from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from apps.users.api import (
    register_app_user_view,
    request_phone_code_view,
    verify_phone_code_view,
)
from core.views import telegram_file

# Global admin polish: clean dash for empty cells + Uzbek titles.
admin.site.empty_value_display = "—"
admin.site.index_title = "Boshqaruv paneli"
# There is no public site. Django defaults this to "/", which puts a
# "Saytni ko'rish" link in the user menu that just bounces back to the admin.
admin.site.site_url = None

urlpatterns = [
    # The admin panel is the whole UI; root just forwards into it.
    path("", RedirectView.as_view(url="/admin/", permanent=False)),
    path("admin/", admin.site.urls),
    # React SPA's DRF backend — see apps/api/.
    path("api/v1/", include("apps.api.urls")),
    # Staff-only proxy to originals that live on Telegram's servers.
    path("tg-file/<str:file_id>/", telegram_file, name="telegram_file"),
    # Mobile app signup hook — API-key authenticated, see apps/users/api.py.
    path("api/app-users/register/", register_app_user_view, name="app_user_register"),
    # Phone sign-in via Eskiz SMS + Firebase custom token — see apps/users/api.py.
    path(
        "api/auth/phone/request-code/",
        request_phone_code_view,
        name="phone_request_code",
    ),
    path(
        "api/auth/phone/verify-code/",
        verify_phone_code_view,
        name="phone_verify_code",
    ),
]

if settings.DEBUG:
    # Media only. Static is auto-served by django.contrib.staticfiles' finders
    # under runserver — adding a STATIC_URL route here would shadow that and
    # 404 app assets (e.g. django-unfold) since STATIC_ROOT is unpopulated.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
