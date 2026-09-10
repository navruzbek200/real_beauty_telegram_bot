from __future__ import annotations

from django.db.models import Max
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.api.pagination import DefaultPagination
from apps.api.permissions import ModelPermissions
from apps.api.serializers.products import (
    BulkUpdateResultSerializer,
    ProductBulkIdsSerializer,
    ProductSerializer,
    ProductTutorialStepSerializer,
    TopProductSerializer,
)
from apps.products.models import Product, ProductTutorialStep, TopProduct


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.prefetch_related("tutorial_steps").all()
    serializer_class = ProductSerializer
    permission_classes = [ModelPermissions]
    pagination_class = DefaultPagination
    filterset_fields = ["is_active", "is_top"]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at", "top_order"]

    @extend_schema(request=ProductBulkIdsSerializer, responses=BulkUpdateResultSerializer)
    @action(detail=False, methods=["post"])
    def add_to_top(self, request):
        serializer = ProductBulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        start = (
            Product.objects.filter(is_top=True).aggregate(top=Max("top_order"))["top"]
            or 0
        )
        qs = Product.objects.filter(pk__in=serializer.validated_data["ids"], is_top=False)
        count = qs.count()
        for offset, product in enumerate(qs, start=1):
            product.is_top = True
            product.top_order = start + offset
            product.save(update_fields=["is_top", "top_order"])
        return Response({"updated": count})

    @extend_schema(request=ProductBulkIdsSerializer, responses=BulkUpdateResultSerializer)
    @action(detail=False, methods=["post"])
    def remove_from_top(self, request):
        serializer = ProductBulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = Product.objects.filter(
            pk__in=serializer.validated_data["ids"]
        ).update(is_top=False)
        return Response({"updated": updated})


class TopProductViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Full curation of the monthly top list, right from its own page.

    A new row here is a brand-new Product with `is_top` forced on — the shop
    picks a place in the top 10 by picking name/price/photo, not by hunting
    through the full catalogue first. "Delete" only clears `is_top`; the
    underlying Product (and its purchase history) is never removed, since
    that FK is CASCADE and would take a customer's buying history with it.
    """

    queryset = TopProduct.objects.prefetch_related("tutorial_steps").all()
    serializer_class = TopProductSerializer
    permission_classes = [ModelPermissions]
    pagination_class = DefaultPagination
    search_fields = ["name", "top_note"]
    ordering_fields = ["top_order", "name"]
    ordering = ["top_order", "name"]

    def perform_create(self, serializer):
        start = (
            Product.objects.filter(is_top=True).aggregate(top=Max("top_order"))["top"]
            or 0
        )
        # `is_active` isn't on this form (the shop only fills in what the top
        # list needs); a brand-new entry must actually show up in the bot, not
        # sit invisible because a multipart POST without the field would
        # otherwise resolve to False.
        serializer.save(is_top=True, top_order=start + 1, is_active=True)

    def perform_destroy(self, instance):
        instance.is_top = False
        instance.save(update_fields=["is_top"])

    @extend_schema(request=ProductBulkIdsSerializer, responses=BulkUpdateResultSerializer)
    @action(detail=False, methods=["post"])
    def reorder(self, request):
        """Set `top_order` from the position of each id in the given list."""
        serializer = ProductBulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]
        updated = 0
        for position, product_id in enumerate(ids, start=1):
            updated += TopProduct.objects.filter(
                pk=product_id, is_top=True
            ).update(top_order=position)
        return Response({"updated": updated})


class ProductTutorialStepViewSet(viewsets.ModelViewSet):
    queryset = ProductTutorialStep.objects.all()
    serializer_class = ProductTutorialStepSerializer
    permission_classes = [ModelPermissions]
    pagination_class = DefaultPagination
    filterset_fields = ["product"]
    ordering_fields = ["order"]

    def perform_create(self, serializer):
        # The CRM form has no protect_content field at all — the bot always
        # sends these videos protected regardless of this flag (see
        # bot/utils/video.py) — but a multipart POST missing a BooleanField
        # resolves to False rather than the model's own default, so a saved
        # row would otherwise misreport itself as unprotected.
        serializer.save(protect_content=True)
