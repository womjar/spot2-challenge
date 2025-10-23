from django.contrib.gis.db import models as gis_models
from django.db import models


class Spot(models.Model):
    # Identifiers and Type based on CSV [cite: 66-68, 89-96]
    spot_id = models.IntegerField(primary_key=True, verbose_name="Spot ID")
    spot_sector_id = models.IntegerField(
        null=True, blank=True, verbose_name="Spot Sector ID"
    )
    spot_type_id = models.IntegerField(
        null=True, blank=True, verbose_name="Spot Type ID"
    )

    # Location Details based on CSV [cite: 69-74, 97-103]
    spot_settlement = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Settlement (Colonia)"
    )
    spot_municipality = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Municipality"
    )
    spot_state = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="State"
    )
    spot_region = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Region"
    )
    spot_corridor = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Corridor"
    )
    spot_address = models.TextField(
        null=True, blank=True, verbose_name="Address"
    )  # Field added based on description [cite: 74, 103]

    # Geospatial Location based on CSV
    # Using PointField from GeoDjango [cite: 131]
    location = gis_models.PointField(
        srid=4326, null=True, blank=True, verbose_name="Geographic Location"
    ) 
    spot_latitude = models.FloatField(
        null=True, blank=True
    ) 
    spot_longitude = models.FloatField(
        null=True, blank=True
    )  

    # Spot Details based on CSV [cite: 75, 76, 79, 104-106]
    spot_title = models.CharField(
        max_length=255, null=True, blank=True, verbose_name="Title"
    )  # Field added based on description [cite: 75, 104]
    spot_description = models.TextField(
        null=True, blank=True, verbose_name="Description"
    )  # Field added based on description [cite: 76, 105]
    spot_area_in_sqm = models.FloatField(
        null=True, blank=True, verbose_name="Area (sqm)"
    )  

    # Pricing Details based on CSV [cite: 80-85, 107-111]
    spot_price_sqm_mxn_rent = models.FloatField(
        null=True, blank=True, verbose_name="Price per sqm Rent (MXN)"
    )
    spot_price_total_mxn_rent = models.FloatField(
        null=True, blank=True, verbose_name="Total Price Rent (MXN)"
    )
    spot_price_sqm_mxn_sale = models.FloatField(
        null=True, blank=True, verbose_name="Price per sqm Sale (MXN)"
    )
    spot_price_total_mxn_sale = models.FloatField(
        null=True, blank=True, verbose_name="Total Price Sale (MXN)"
    )
    spot_maintenance_cost = models.FloatField(
        null=True, blank=True, verbose_name="Maintenance Cost (MXN)"
    )  # Assuming this maps to 'Spot Maintenance Cost MXN' [cite: 84, 85, 111]

    # Other Details based on CSV [cite: 86-88, 112-115]
    spot_modality = models.CharField(
        max_length=100, null=True, blank=True, verbose_name="Modality (Rent/Sale/Both)"
    )
    user_id = models.IntegerField(
        null=True, blank=True, verbose_name="User ID"
    )  # Renamed from uuiid [cite: 144] based on description [cite: 87, 114]
    spot_created_date = models.DateField(
        null=True, blank=True, verbose_name="Created Date"
    )

    data_source = models.CharField(max_length=10, default='csv', help_text="Source of the data (e.g., 'csv', 'json')")
    public_id = models.CharField(max_length=50, null=True, blank=True, unique=True, help_text="Public ID from external source (e.g., EB-PV4135)")

    def __str__(self):
        return f"Spot {self.spot_id} ({self.spot_municipality})"

    class Meta:
        verbose_name = "Spot"
        verbose_name_plural = "Spots"
        ordering = ["spot_id"] 
        indexes = [
            gis_models.Index(fields=["location"]),
        ]
