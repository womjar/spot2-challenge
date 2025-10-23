# spots/tests.py

import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.gis.geos import Point, Polygon
from .models import Spot
from django.db.models import Avg  # Para verificar el promedio


class SpotAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        # Datos de prueba más diversos
        cls.spot1 = Spot.objects.create(
            spot_id=101,
            spot_municipality="Test A",
            spot_state="State X",
            location=Point(-99.1, 19.1, srid=4326),
            spot_price_total_mxn_rent=15000.0,
            spot_area_in_sqm=100.0,
            spot_sector_id=9,
            spot_type_id=1,
            spot_created_date="2024-01-15",
        )
        cls.spot2 = Spot.objects.create(
            spot_id=102,
            spot_municipality="Test B",
            spot_state="State Y",
            location=Point(-99.2, 19.2, srid=4326),
            spot_price_total_mxn_rent=25000.0,
            spot_area_in_sqm=200.0,
            spot_sector_id=11,
            spot_type_id=1,
            spot_created_date="2024-03-20",
        )
        cls.spot3 = Spot.objects.create(
            spot_id=103,
            spot_municipality="Test A",
            spot_state="State X",
            location=Point(-99.15, 19.15, srid=4326),
            spot_price_total_mxn_rent=10000.0,  # Precio menor
            spot_area_in_sqm=50.0,
            spot_sector_id=9,
            spot_type_id=2,
            spot_created_date="2024-02-10",
        )
        # Spot sin precio de renta para pruebas de agregación/ordenamiento
        cls.spot4 = Spot.objects.create(
            spot_id=104,
            spot_municipality="Test C",
            spot_state="State Z",
            location=Point(-99.3, 19.3, srid=4326),
            spot_price_total_mxn_rent=None,
            spot_area_in_sqm=300.0,
            spot_sector_id=11,
            spot_type_id=1,
            spot_created_date="2024-04-01",
        )

    # --- Pruebas de Listado, Filtrado, Ordenamiento y Paginación ---

    def test_list_spots_paginated(self):
        """Verifica el listado y la paginación por defecto."""
        url = reverse("spot-list")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Asumiendo PAGE_SIZE=25 (o lo que configures), todos deberían estar en la primera página
        self.assertEqual(response.data["count"], 4)
        self.assertEqual(len(response.data["results"]), 4)
        self.assertIn("next", response.data)  # Verifica claves de paginación
        self.assertIn("previous", response.data)

    def test_filter_by_sector(self):
        """Verifica el filtrado por sector_id."""
        url = reverse("spot-list") + "?sector=9"
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        spot_ids = {
            spot["properties"]["spot_id"]
            for spot in response.data["results"]["features"]
        }
        self.assertEqual(spot_ids, {101, 103})

    def test_filter_by_municipality(self):
        """Verifica el filtrado por municipio (case-insensitive)."""
        url = reverse("spot-list") + "?municipality=test a"  # Minúsculas
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        spot_ids = {
            spot["properties"]["spot_id"]
            for spot in response.data["results"]["features"]
        }
        self.assertEqual(spot_ids, {101, 103})

    def test_filter_combined(self):
        """Verifica el filtrado combinado."""
        url = reverse("spot-list") + "?sector=9&type=1"
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"]["features"][0]["properties"]["spot_id"], 101
        )

    def test_ordering_by_rent_desc(self):
        """Verifica el ordenamiento descendente por precio de renta."""
        url = reverse("spot-list") + "?ordering=-spot_price_total_mxn_rent"
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Spot4 (None) debería ser excluido o ir al final dependiendo de la BD,
        # aquí verificamos los que tienen precio
        ids_ordered = [
            spot["properties"]["spot_id"]
            for spot in response.data["results"]["features"]
        ]
        # Esperamos 102 (25k), 101 (15k), 103 (10k), posiblemente 104 (None) al final
        self.assertListEqual(ids_ordered[:3], [102, 101, 103])

    def test_ordering_by_area_asc(self):
        """Verifica el ordenamiento ascendente por área."""
        url = reverse("spot-list") + "?ordering=spot_area_in_sqm"
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids_ordered = [
            spot["properties"]["spot_id"]
            for spot in response.data["results"]["features"]
        ]
        self.assertListEqual(ids_ordered, [103, 101, 102, 104])  # 50, 100, 200, 300

    # --- Pruebas de Endpoints Específicos ---

    def test_spot_detail_found(self):
        """Verifica obtener el detalle de un spot existente."""
        url = reverse("spot-detail", kwargs={"spot_id": self.spot1.spot_id})
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["properties"]["spot_municipality"],
            self.spot1.spot_municipality,
        )
        self.assertEqual(response.data["geometry"]["type"], "Point")

    def test_spot_detail_not_found(self):
        """Verifica que un spot no existente devuelva 404."""
        url = reverse("spot-detail", kwargs={"spot_id": 9999})  # ID no existente
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_nearby_spots(self):
        """Verifica la búsqueda de spots cercanos."""
        url = reverse("spot-nearby")
        # Punto cerca de spot1 (-99.1, 19.1) -> Distancia ~11km
        # Punto cerca de spot3 (-99.15, 19.15) -> Distancia ~5.5km
        # Radio de 6km debería encontrar solo spot3
        response = self.client.get(
            url + "?lng=-99.151&lat=19.151&radius=6000", format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["features"]), 1)
        self.assertEqual(response.data["features"][0]["properties"]["spot_id"], 103)

    def test_nearby_spots_finds_multiple(self):
        """Verifica que nearby encuentre múltiples spots si están dentro del radio."""
        url = reverse("spot-nearby")
        # Punto intermedio y radio grande para incluir spot1 y spot3
        response = self.client.get(
            url + "?lng=-99.12&lat=19.12&radius=50000", format="json"
        )  # Radio 50km
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(
            len(response.data["features"]), 2
        )  # Debería encontrar al menos spot1 y spot3
        spot_ids = {spot["properties"]["spot_id"] for spot in response.data["features"]}
        self.assertIn(101, spot_ids)
        self.assertIn(103, spot_ids)

    def test_within_polygon(self):
        """Verifica la búsqueda de spots dentro de un polígono."""
        url = reverse("spot-within")
        # Polígono que solo encierra a spot1 (-99.1, 19.1)
        polygon_coords = [
            [
                [-99.11, 19.09],
                [-99.09, 19.09],
                [-99.09, 19.11],
                [-99.11, 19.11],
                [-99.11, 19.09],  # Cerrar polígono
            ]
        ]
        data = {"polygon": {"type": "Polygon", "coordinates": polygon_coords}}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["features"]), 1)
        self.assertEqual(response.data["features"][0]["properties"]["spot_id"], 101)

    def test_within_polygon_empty(self):
        """Verifica que within devuelva vacío si no hay spots dentro."""
        url = reverse("spot-within")
        # Polígono en una zona vacía
        polygon_coords = [
            [
                [-100.0, 20.0],
                [-100.1, 20.0],
                [-100.1, 20.1],
                [-100.0, 20.1],
                [-100.0, 20.0],
            ]
        ]
        data = {"polygon": {"type": "Polygon", "coordinates": polygon_coords}}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["features"]), 0)

    def test_average_price_by_sector(self):
        """Verifica el cálculo del precio promedio por sector."""
        url = reverse("spot-avg-price")
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data), 2
        )  # Deberían haber 2 sectores (9 y 11) con precios

        expected_avg_sector_9 = (15000.0 + 10000.0) / 2  # Spots 101 y 103
        expected_avg_sector_11 = 25000.0 / 1  # Solo Spot 102 (Spot 104 es None)

        results = {
            item["spot_sector_id"]: item["average_price"] for item in response.data
        }
        self.assertAlmostEqual(results[9], expected_avg_sector_9, places=2)
        self.assertAlmostEqual(results[11], expected_avg_sector_11, places=2)

    def test_top_rent(self):
        """Verifica el ranking por precio de renta con límite."""
        url = reverse("spot-top-rent") + "?limit=2"
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["features"]), 2)  # Respetar el límite
        # Verificar el orden descendente
        self.assertEqual(
            response.data["features"][0]["properties"]["spot_id"], 102
        )  # 25k
        self.assertEqual(
            response.data["features"][1]["properties"]["spot_id"], 101
        )  # 15k
