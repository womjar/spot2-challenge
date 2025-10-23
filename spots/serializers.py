from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers
from .models import Spot


class SpotSerializer(GeoFeatureModelSerializer):
    """A class to serialize locations as GeoJSON compatible data"""

    class Meta:
        model = Spot
        geo_field = "location"  

        fields = (
            "spot_id",
            "spot_sector_id",
            "spot_type_id",
            "spot_settlement",
            "spot_municipality",
            "spot_state",
            "spot_region",
            "spot_corridor",
            "spot_address",
            "spot_title",
            "spot_description",
            "location", 
            "spot_area_in_sqm",
            "spot_price_sqm_mxn_rent",
            "spot_price_total_mxn_rent",
            "spot_price_sqm_mxn_sale",
            "spot_price_total_mxn_sale",
            "spot_maintenance_cost",
            "spot_modality",
            "user_id",
            "spot_created_date",
        )
        read_only_fields = ("location",) 


class AvgPriceSerializer(serializers.Serializer):
    """Serializer for the average price aggregated data"""

    spot_sector_id = serializers.IntegerField()
    average_price = serializers.FloatField()
