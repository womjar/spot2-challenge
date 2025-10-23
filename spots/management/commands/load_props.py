import json
import os
import time  # Para añadir un pequeño delay en geocoding
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.contrib.gis.geos import Point
from django.db.models import Max  # Para obtener el máximo ID existente
from spots.models import Spot
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Loads, normalizes, and geocodes spot data from props_list.json into the Spot model"

    def handle(self, *args, **options):
        file_path = os.path.join(settings.BASE_DIR, "data", "props_list.json")
        self.stdout.write(f"Looking for JSON file at: {file_path}")

        if not os.path.exists(file_path):
            raise CommandError(f"JSON file not found at {file_path}")

        try:
            with open(file_path, mode="r", encoding="utf-8") as jsonfile:
                data = json.load(jsonfile)
        except json.JSONDecodeError as e:
            raise CommandError(f"Error decoding JSON: {e}")
        except Exception as e:
            raise CommandError(f"Error reading file: {e}")

        # --- Preparación para Geocoding y ID ---
        geolocator = Nominatim(user_agent="spot_loader_app")  # Necesario para Nominatim
        # Encontrar el máximo spot_id existente para generar nuevos IDs
        max_id_result = Spot.objects.aggregate(max_id=Max("spot_id"))
        current_max_id = (
            max_id_result["max_id"] if max_id_result["max_id"] is not None else 0
        )
        next_spot_id = current_max_id + 1
        self.stdout.write(
            f"Max existing spot_id: {current_max_id}. Starting new IDs from {next_spot_id}."
        )

        created_count = 0
        updated_count = 0
        skipped_count = 0
        geocode_errors = 0

        for idx, item in enumerate(data):
            public_id = item.get("public_id")
            if not public_id:
                self.stdout.write(
                    self.style.WARNING(f"Skipping item {idx + 1}: Missing public_id")
                )
                skipped_count += 1
                continue

            # Datos base para actualizar o crear
            defaults_data = {"data_source": "json"}

            # --- Normalización ---
            location_str = item.get("location", "")
            parts = [part.strip() for part in location_str.split(",")]
            if len(parts) >= 3:
                defaults_data["spot_state"] = parts[-1]
                defaults_data["spot_municipality"] = parts[-2]
                defaults_data["spot_settlement"] = (
                    ", ".join(parts[:-2]) if len(parts) > 2 else None
                )
            elif len(parts) == 2:
                defaults_data["spot_municipality"] = parts[-1]
                defaults_data["spot_settlement"] = parts[0]
            elif len(parts) == 1 and parts[0]:
                defaults_data["spot_municipality"] = parts[0]

            construction_size = item.get("construction_size")
            if construction_size is not None:
                try:
                    defaults_data["spot_area_in_sqm"] = float(construction_size)
                except (ValueError, TypeError):
                    defaults_data["spot_area_in_sqm"] = None

            operations = item.get("operations", [])
            is_sale = False
            is_rent = False
            for op in operations:
                op_type = op.get("type")
                amount = op.get("amount")
                currency = op.get("currency", "MXN")
                if amount is not None and currency == "MXN":
                    try:
                        price = float(amount)
                        if op_type == "sale":
                            defaults_data["spot_price_total_mxn_sale"] = price
                            is_sale = True
                        elif op_type == "rental":
                            defaults_data["spot_price_total_mxn_rent"] = price
                            is_rent = True
                    except (ValueError, TypeError):
                        pass

            if is_sale and is_rent:
                defaults_data["spot_modality"] = "Rent & Sale"
            elif is_sale:
                defaults_data["spot_modality"] = "Sale"
            elif is_rent:
                defaults_data["spot_modality"] = "Rent"

            defaults_data["spot_title"] = item.get("title")
            updated_at_str = item.get("updated_at")
            if updated_at_str:
                try:
                    dt = parse_datetime(updated_at_str)
                    if dt:
                        defaults_data["spot_created_date"] = dt.date()
                except ValueError:
                    pass

            # --- Geocodificación ---
            latitude, longitude = None, None
            location_point = None
            if location_str:
                try:
                    location_geo = geolocator.geocode(
                        location_str, timeout=10
                    )  # Intentar geocodificar
                    if location_geo:
                        latitude = location_geo.latitude
                        longitude = location_geo.longitude
                        location_point = Point(longitude, latitude, srid=4326)
                        defaults_data["spot_latitude"] = latitude
                        defaults_data["spot_longitude"] = longitude
                        defaults_data["location"] = location_point
                        self.stdout.write(
                            f"Geocoded '{location_str}' to ({latitude}, {longitude})"
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Could not geocode address for {public_id}: '{location_str}'"
                            )
                        )
                        geocode_errors += 1
                    time.sleep(
                        1
                    )  # IMPORTANTE: Respetar los límites de uso de Nominatim (1 req/sec)
                except (GeocoderTimedOut, GeocoderServiceError) as e:
                    self.stdout.write(
                        self.style.ERROR(f"Geocoding error for {public_id}: {e}")
                    )
                    geocode_errors += 1
                    time.sleep(1)  # Esperar antes de reintentar con el siguiente
                except Exception as e:
                    logger.exception(f"Unexpected geocoding error for {public_id}")
                    geocode_errors += 1
                    time.sleep(1)

            # --- Fin Normalización y Geocodificación ---

            # Usar get_or_create basado en public_id
            try:
                # Datos que se usarán SOLO si se CREA un nuevo objeto
                create_defaults = defaults_data.copy()
                create_defaults["spot_id"] = (
                    next_spot_id  # Asignar el nuevo ID numérico
                )

                obj, created = Spot.objects.get_or_create(
                    public_id=public_id,
                    defaults=create_defaults,  # Usar todos los datos (incluido spot_id) al crear
                )

                if created:
                    created_count += 1
                    next_spot_id += 1  # Incrementar solo si se creó uno nuevo
                    self.stdout.write(
                        f"Created new spot with ID {obj.spot_id} for public_id {public_id}"
                    )
                else:
                    # Si ya existía, actualízalo con los datos (sin incluir spot_id en la actualización)
                    updated = False
                    for key, value in defaults_data.items():
                        # Actualizar solo si el valor nuevo es diferente del existente (y no es None)
                        if value is not None and getattr(obj, key) != value:
                            setattr(obj, key, value)
                            updated = True
                    if updated:
                        obj.save()
                        updated_count += 1
                        self.stdout.write(f"Updated spot with public_id {public_id}")
                    # else:
                    #     self.stdout.write(f"No changes detected for public_id {public_id}")

            except IntegrityError as e:
                # Podría ocurrir si hay un problema con la unicidad de public_id u otro constraint
                self.stderr.write(
                    self.style.ERROR(
                        f"Integrity error for item {idx + 1} (ID: {public_id}): {e}"
                    )
                )
                logger.exception(
                    f"Integrity error processing item {idx + 1} (ID: {public_id}) with data: {item}"
                )
                skipped_count += 1
            except Exception as e:
                self.stderr.write(
                    self.style.ERROR(
                        f"Error processing item {idx + 1} (ID: {public_id}): {e}"
                    )
                )
                logger.exception(
                    f"Error processing item {idx + 1} (ID: {public_id}) with data: {item}"
                )
                skipped_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully processed {idx + 1} items. "
                f"Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count}. "
                f"Geocoding Errors/Not Found: {geocode_errors}."
            )
        )
