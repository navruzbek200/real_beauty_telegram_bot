from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.pagination import DefaultPagination
from apps.api.permissions import IsSuperUser, ModelPermissions
from apps.api.serializers.bot_settings import DiscountSerializer, GlobalSettingsSerializer
from apps.bot_settings.models import Discount, GlobalSettings


class GlobalSettingsView(APIView):
    permission_classes = [IsSuperUser]

    @extend_schema(responses=GlobalSettingsSerializer)
    def get(self, request):
        return Response(GlobalSettingsSerializer(GlobalSettings.get()).data)

    @extend_schema(request=GlobalSettingsSerializer, responses=GlobalSettingsSerializer)
    def patch(self, request):
        settings = GlobalSettings.get()
        serializer = GlobalSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class DiscountViewSet(viewsets.ModelViewSet):
    queryset = Discount.objects.all()
    serializer_class = DiscountSerializer
    permission_classes = [ModelPermissions]
    pagination_class = DefaultPagination
    filterset_fields = ["is_active"]
    search_fields = ["title", "promo_code", "description"]
    ordering_fields = ["created_at", "valid_until"]
