from __future__ import annotations

from rest_framework import serializers


class DetailMessageSerializer(serializers.Serializer):
    """Shape of a plain {"detail": "..."} response, for actions that don't
    return a model instance (test-sends, connection checks, bulk triggers)."""

    detail = serializers.CharField()
