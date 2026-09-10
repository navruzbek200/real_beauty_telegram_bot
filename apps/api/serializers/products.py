from __future__ import annotations

from rest_framework import serializers

from apps.products.models import Product, ProductTutorialStep, TopProduct


class ProductTutorialStepSerializer(serializers.ModelSerializer):
    has_video = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProductTutorialStep
        fields = [
            "id",
            "product",
            "order",
            "button_label",
            "button_label_ru",
            "button_label_en",
            "intro_text",
            "intro_text_ru",
            "intro_text_en",
            "video_file",
            "protect_content",
            "has_video",
        ]


class ProductSerializer(serializers.ModelSerializer):
    tutorial_steps = ProductTutorialStepSerializer(many=True, read_only=True)
    buyers_count = serializers.IntegerField(source="userproduct_set.count", read_only=True)
    discount_percent = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "name_ru",
            "name_en",
            "description",
            "description_ru",
            "description_en",
            "photo",
            "is_active",
            "current_price",
            "old_price",
            "discount_percent",
            "is_top",
            "top_order",
            "top_note",
            "top_note_ru",
            "top_note_en",
            "created_at",
            "tutorial_steps",
            "buyers_count",
        ]
        read_only_fields = ["created_at"]


class TopProductSerializer(ProductSerializer):
    class Meta(ProductSerializer.Meta):
        model = TopProduct


class ProductBulkIdsSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)


class BulkUpdateResultSerializer(serializers.Serializer):
    updated = serializers.IntegerField()
