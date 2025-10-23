import json
from django.contrib.gis.geos import Point, GEOSGeometry
from django.contrib.gis.measure import D  # Distance object
from django.db.models import Avg, F
from django.db.models.functions import Cast
from django.db.models import FloatField
from rest_framework import generics, views, status
from rest_framework.response import Response
from rest_framework_gis.filters import DistanceToPointFilter
from django_filters.rest_framework import (
    DjangoFilterBackend,
    FilterSet,
    CharFilter,
    NumberFilter,
)

from .models import Spot
from .serializers import SpotSerializer, AvgPriceSerializer


class SpotFilter(FilterSet):
    """Custom filterset for Spot attributes"""

    sector = NumberFilter(field_name="spot_sector_id")
    type = NumberFilter(field_name="spot_type_id")
    municipality = CharFilter(
        field_name="spot_municipality", lookup_expr="icontains"
    ) 

    class Meta:
        model = Spot
        fields = ["sector", "type", "municipality"]


class SpotListCreateView(generics.ListAPIView):
    """
    API view to list all spots or filter by attributes.
    GET /api/spots/
    GET /api/spots/?sector=9&type=1&municipality=Álvaro Obregón [cite: 24]
    """

    queryset = Spot.objects.all()
    serializer_class = SpotSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = SpotFilter



class SpotNearbyView(generics.ListAPIView):
    """
    API view to find spots near a given point (lat, lng) within a radius (in meters).
    GET /api/spots/nearby/?lat=19.4326&lng=-99.1332&radius=2000 [cite: 22]
    """

    queryset = Spot.objects.all()
    serializer_class = SpotSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        lat = self.request.query_params.get("lat")
        lng = self.request.query_params.get("lng")
        radius = self.request.query_params.get("radius") 

        if lat and lng and radius:
            try:
                ref_point = Point(
                    float(lng), float(lat), srid=4326
                )  
                radius_m = float(radius)
                queryset = (
                    queryset.filter(location__distance_lte=(ref_point, D(m=radius_m)))
                    .annotate(
                        distance=Cast(
                            0.0, FloatField()
                        ) 
                    )
                    .order_by("distance")
                ) 
            except (ValueError, TypeError):
                return Spot.objects.none() 
        else:
            return Spot.objects.none()

        return queryset


class SpotWithinView(views.APIView):
    """
    API view to find spots within a given polygon.
    POST /api/spots/within/ [cite: 26]
    Requires a JSON body with a GeoJSON Polygon:
    {
      "polygon": {
        "type": "Polygon",
        "coordinates": [[[lng1, lat1], [lng2, lat2], ...]]
      }
    }
    """

    def post(self, request, *args, **kwargs):
        polygon_data = request.data.get("polygon")

        if not polygon_data:
            return Response(
                {"error": "Missing 'polygon' in request body."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if isinstance(polygon_data, str):
                polygon_data = json.loads(polygon_data)

            polygon = GEOSGeometry(json.dumps(polygon_data), srid=4326)

            if not polygon.geom_type == "Polygon":
                return Response(
                    {"error": "Geometry type must be 'Polygon'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except (json.JSONDecodeError, TypeError, ValueError, Exception) as e:
            return Response(
                {"error": f"Invalid polygon data provided. {e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = Spot.objects.filter(location__within=polygon)
        serializer = SpotSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)


class SpotAveragePriceBySectorView(views.APIView):
    """
    API view to calculate the average total rent price per sector.
    GET /api/spots/average-price-by-sector/ [cite: 33]
    """

    def get(self, request, *args, **kwargs):
        avg_prices = (
            Spot.objects.filter(spot_price_total_mxn_rent__isnull=False)
            .values("spot_sector_id")
            .annotate(average_price=Avg("spot_price_total_mxn_rent"))
            .order_by("spot_sector_id")
        )

        serializer = AvgPriceSerializer(avg_prices, many=True)
        return Response(serializer.data)


class SpotDetailView(generics.RetrieveAPIView):
    """
    API view to retrieve details of a specific spot by its ID.
    GET /api/spots/{spot_id}/ [cite: 35]
    """

    queryset = Spot.objects.all()
    serializer_class = SpotSerializer
    lookup_field = "spot_id"  


class SpotTopRentView(generics.ListAPIView):
    """
    API view to rank spots by total rent price.
    GET /api/spots/top-rent/?limit=10 [cite: 37]
    """

    serializer_class = SpotSerializer

    def get_queryset(self):
        limit_param = self.request.query_params.get("limit", "10") 
        try:
            limit = int(limit_param)
            if limit <= 0:
                limit = 10  
        except ValueError:
            limit = 10 

        queryset = Spot.objects.filter(
            spot_price_total_mxn_rent__isnull=False
        ).order_by("-spot_price_total_mxn_rent")[:limit] 

        return queryset
