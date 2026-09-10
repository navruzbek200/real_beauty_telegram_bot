from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.pagination import DefaultPagination
from apps.api.permissions import IsSuperUser
from apps.api.serializers.loyalty import LoyaltySettingsSerializer, RewardSerializer
from apps.loyalty.models import LoyaltySettings, Reward


class LoyaltySettingsView(APIView):
    """The whole points/cashback economy on one endpoint — superuser only."""

    permission_classes = [IsSuperUser]

    @extend_schema(responses=LoyaltySettingsSerializer)
    def get(self, request):
        return Response(LoyaltySettingsSerializer(LoyaltySettings.get()).data)

    @extend_schema(
        request=LoyaltySettingsSerializer, responses=LoyaltySettingsSerializer
    )
    def patch(self, request):
        settings = LoyaltySettings.get()
        serializer = LoyaltySettingsSerializer(
            settings, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class RewardViewSet(viewsets.ModelViewSet):
    queryset = Reward.objects.all()
    serializer_class = RewardSerializer
    permission_classes = [IsSuperUser]
    pagination_class = DefaultPagination
    filterset_fields = ["is_active"]
    search_fields = ["title", "title_ru", "title_en", "description"]
    ordering_fields = ["cost_points", "created_at"]
