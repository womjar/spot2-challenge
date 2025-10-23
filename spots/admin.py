from django.contrib.gis import admin 
from .models import Spot

@admin.register(Spot)
class SpotAdmin(admin.ModelAdmin):
    list_display = (
        "spot_id",
        "spot_municipality",
        "spot_state",
        "spot_sector_id",
        "spot_type_id",
        "spot_modality",
        "spot_area_in_sqm",
        "spot_price_total_mxn_rent",
        "spot_created_date",
    )
    list_filter = ("spot_state", "spot_municipality", "spot_sector_id", "spot_modality")
    search_fields = (
        "spot_id",
        "spot_municipality",
        "spot_settlement",
        "spot_address",
        "spot_title",
    )
    readonly_fields = (
        "spot_latitude",
        "spot_longitude",
    ) 
    ordering = ("-spot_created_date", "spot_id")
    default_lat = 19.4326
    default_lon = -99.1332
    default_zoom = 10
