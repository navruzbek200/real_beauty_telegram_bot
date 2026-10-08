"""The gated course, from the React panel."""

from __future__ import annotations

from django.db import IntegrityError
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.api.permissions import ModelPermissions
from apps.api.pagination import DefaultPagination
from apps.api.serializers.lessons import (
    AccessCodeSerializer,
    IssueCodesSerializer,
    IssuedCodesResultSerializer,
    LessonUnlockSerializer,
    LessonVideoSerializer,
)
from apps.lessons.models import AccessCode, LessonUnlock, LessonVideo, generate_code


class LessonVideoViewSet(viewsets.ModelViewSet):
    queryset = LessonVideo.objects.all()
    serializer_class = LessonVideoSerializer
    permission_classes = [ModelPermissions]
    pagination_class = DefaultPagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    filterset_fields = ["is_active"]
    search_fields = ["title", "title_ru", "title_en"]
    ordering_fields = ["order", "created_at", "title"]
    ordering = ["order", "id"]


class AccessCodeViewSet(viewsets.ModelViewSet):
    serializer_class = AccessCodeSerializer
    permission_classes = [ModelPermissions]
    pagination_class = DefaultPagination
    filterset_fields = ["is_active"]
    search_fields = ["code", "label", "issued_to__full_name"]
    ordering_fields = ["created_at", "code", "uses_count"]
    ordering = ["-created_at", "id"]

    # One press at the counter never needs more, and a number typed by a
    # client never reaches the database unchecked.
    MAX_ISSUE = 50

    def get_queryset(self):
        qs = (
            AccessCode.objects.select_related("issued_to")
            .prefetch_related("unlocks__user")
            .all()
        )
        # The question a seller actually asks is "which of these can I still
        # hand out?", and is_active cannot answer it — a code can be active
        # and already spent, which is where most of them end up.
        state = self.request.query_params.get("state")
        now = timezone.now()
        if state == "free":
            return qs.filter(is_active=True, uses_count=0).exclude(expires_at__lte=now)
        if state == "used":
            return qs.filter(uses_count__gt=0)
        if state == "expired":
            return qs.filter(expires_at__lte=now)
        if state == "off":
            return qs.filter(is_active=False)
        return qs

    def perform_create(self, serializer):
        # An empty code from the form means "give me one" — the model fills it
        # in, so the shop never has to invent a word it can't remember.
        serializer.save()

    @extend_schema(request=IssueCodesSerializer, responses=IssuedCodesResultSerializer)
    @action(detail=False, methods=["post"])
    def issue(self, request):
        """Mint single-use codes and hand them back once.

        The response is the only time these are shown as a set — a code
        matters in the seconds between minting it and reading it out.
        """
        serializer = IssueCodesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        count = min(serializer.validated_data["count"], self.MAX_ISSUE)
        label = serializer.validated_data.get("label") or "Xarid uchun"

        made: list[str] = []
        for _ in range(count):
            # A collision over 31^8 is vanishingly unlikely, but "unlikely" is
            # not "handled" — retry rather than fail the whole batch.
            for _attempt in range(5):
                candidate = generate_code()
                try:
                    AccessCode.objects.create(code=candidate, max_uses=1, label=label)
                except IntegrityError:
                    continue
                made.append(candidate)
                break
        return Response({"codes": made})


class LessonUnlockViewSet(
    viewsets.mixins.ListModelMixin,
    viewsets.mixins.CreateModelMixin,
    viewsets.mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Who has the course open — and the way to open it by hand.

    Access is keyed on the Telegram account, so a customer who deletes
    Telegram and signs up again arrives as a different person with a code
    that is already spent. Creating a row here is the one-step answer;
    deleting one takes the course back.
    """

    serializer_class = LessonUnlockSerializer
    permission_classes = [ModelPermissions]
    pagination_class = DefaultPagination
    search_fields = ["user__full_name", "user__phone_number", "code__code"]
    ordering_fields = ["unlocked_at"]
    ordering = ["-unlocked_at"]

    def get_queryset(self):
        return LessonUnlock.objects.select_related("user", "code").all()
