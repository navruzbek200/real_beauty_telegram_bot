from __future__ import annotations

import logging

from rest_framework import mixins, viewsets

from apps.analytics.models import SkinQuizResult
from apps.api.pagination import DefaultPagination
from apps.api.permissions import ModelPermissions
from apps.api.serializers.analytics import SkinQuizResultSerializer

logger = logging.getLogger(__name__)


class SkinQuizResultViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = SkinQuizResult.objects.select_related("user").all()
    serializer_class = SkinQuizResultSerializer
    permission_classes = [ModelPermissions]
    pagination_class = DefaultPagination
    filterset_fields = ["skin_type", "language"]
    search_fields = ["user__full_name", "user__phone_number"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
