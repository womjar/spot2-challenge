import csv
import os
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from django.conf import settings
from django.utils.dateparse import parse_date
from spots.models import Spot
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Loads spot data from lk_spots.csv into the Spot model"

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv_path',
            type=str,
            help='Optional path to the CSV file to load',
            default=os.path.join(settings.BASE_DIR, 'data', 'lk_spots.csv') # Default path
        )

    def handle(self, *args, **options):
        file_path = options["csv_path"]
        self.stdout.write(f"Looking for CSV file at: {file_path}")

        if not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR(f"CSV file not found at {file_path}"))
            return

        # Define expected headers based on the CSV file [cite: 144]
        expected_headers = [
            "spot_id",
            "spot_sector_id",
            "spot_type_id",
            "spot_settlement",
            "spot_municipality",
            "spot_state",
            "spot_region",
            "spot_corridor",
            "spot_latitude",
            "spot_longitude",
            "spot_area_in_sqm",
            "spot_price_sqm_mxn_rent",
            "spot_price_total_mxn_rent",
            "spot_price_sqm_mxn_sale",
            "spot_price_total_mxn_sale",
            "spot_modality",
            "uuiid",
            "spot_created_date",
            # Note: spot_address, spot_title, spot_description, spot_maintenance_cost are not in the CSV header provided [cite: 144]
        ]

        count = 0
        created_count = 0
        updated_count = 0

        try:
            with open(file_path, mode="r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)

                # Verify headers
                if not all(header in reader.fieldnames for header in expected_headers):
                    missing = [
                        h for h in expected_headers if h not in reader.fieldnames
                    ]
                    extra = [h for h in reader.fieldnames if h not in expected_headers]
                    self.stderr.write(
                        self.style.ERROR(
                            f"CSV header mismatch. Missing: {missing}. Extra found: {extra}. Check CSV file and expected_headers."
                        )
                    )
                    return

                for row in reader:
                    count += 1
                    spot_id = row.get("spot_id")
                    lat_str = row.get("spot_latitude")
                    lon_str = row.get("spot_longitude")

                    if not spot_id:
                        self.stdout.write(
                            self.style.WARNING(f"Skipping row {count}: Missing spot_id")
                        )
                        continue

                    spot_data = {}
                    location = None

                    # Handle PointField creation [cite: 131]
                    if lat_str and lon_str:
                        try:
                            latitude = float(lat_str)
                            longitude = float(lon_str)
                            location = Point(
                                longitude, latitude, srid=4326
                            ) 
                            spot_data["spot_latitude"] = (
                                latitude 
                            )
                            spot_data["spot_longitude"] = longitude
                        except (ValueError, TypeError) as e:
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Skipping row {count} (ID: {spot_id}): Invalid coordinates '{lat_str}', '{lon_str}'. Error: {e}"
                                )
                            )
                            location = None  

                    spot_data["location"] = location

                    fields_map = {
                        "spot_sector_id": int,
                        "spot_type_id": int,
                        "spot_settlement": str,
                        "spot_municipality": str,
                        "spot_state": str,
                        "spot_region": str,
                        "spot_corridor": str,
                        "spot_area_in_sqm": float,
                        "spot_price_sqm_mxn_rent": float,
                        "spot_price_total_mxn_rent": float,
                        "spot_price_sqm_mxn_sale": float,
                        "spot_price_total_mxn_sale": float,
                        "spot_modality": str,
                        "user_id": int,  
                        "spot_created_date": parse_date,
                    }

                    source_field_map = {
                        "user_id": "uuiid"
                    }  

                    for model_field, converter in fields_map.items():
                        csv_field_name = source_field_map.get(model_field, model_field)
                        value = row.get(csv_field_name, "").strip()
                        if value:
                            try:
                                spot_data[model_field] = converter(value)
                            except (ValueError, TypeError, InvalidOperation) as e:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"Row {count} (ID: {spot_id}): Invalid value '{value}' for {model_field}. Setting to None. Error: {e}"
                                    )
                                )
                                spot_data[model_field] = None
                        else:
                            spot_data[model_field] = None  

                    try:
                        spot_id_int = int(spot_id)
                        obj, created = Spot.objects.update_or_create(
                            spot_id=spot_id_int, defaults=spot_data
                        )
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    except ValueError:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipping row {count}: Invalid spot_id '{spot_id}'"
                            )
                        )
                    except Exception as e:
                        self.stderr.write(
                            self.style.ERROR(
                                f"Error processing row {count} (ID: {spot_id}): {e}"
                            )
                        )
                        logger.exception(
                            f"Error processing row {count} (ID: {spot_id}) with data: {row}"
                        )

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"File not found at {file_path}"))
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An unexpected error occurred: {e}"))
            logger.exception("An unexpected error occurred during CSV processing.")
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully processed {count} rows. Created: {created_count}, Updated: {updated_count}."
            )
        )
