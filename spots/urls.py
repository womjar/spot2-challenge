from django.urls import path
from . import views

urlpatterns = [
    path(
        "spots/", views.SpotListCreateView.as_view(), name="spot-list"
    ),  # List and Filter [cite: 20, 24]
    path(
        "spots/nearby/", views.SpotNearbyView.as_view(), name="spot-nearby"
    ),  # Nearby search [cite: 22]
    path(
        "spots/within/", views.SpotWithinView.as_view(), name="spot-within"
    ),  # Within polygon search [cite: 26]
    path(
        "spots/average-price-by-sector/",
        views.SpotAveragePriceBySectorView.as_view(),
        name="spot-avg-price",
    ),  # Avg price [cite: 33]
    path(
        "spots/top-rent/", views.SpotTopRentView.as_view(), name="spot-top-rent"
    ),  # Top rent [cite: 37]
    path(
        "spots/<int:spot_id>/", views.SpotDetailView.as_view(), name="spot-detail"
    ),  # Detail view [cite: 35]
]
