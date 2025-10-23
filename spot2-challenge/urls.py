from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)  # For Stage 2

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("spots.urls")),  # Include spots app URLs
    # API Schema and Docs URLs (for Stage 2)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]
