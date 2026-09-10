"""
Public, read-only catalogue + lessons for the Telegram Mini App.

The Mini App is a shopfront — the same product names, prices and photos a
customer already sees inside the bot — so it is deliberately unauthenticated
and read-only. Nothing here exposes anything a customer couldn't see by tapping
«Mahsulotlar» in the chat. Writes still go through the authenticated admin API.

The lessons endpoint *personalizes* (shows the customer's own products first)
only when the request carries a Telegram `initData` string whose HMAC checks
out against our bot token — the standard Mini App authentication scheme. A
missing or forged initData silently falls back to the generic list, so the
endpoint still never exposes anything private.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from urllib.parse import parse_qsl

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from rest_framework import status as http_status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.products.models import Product
from core.i18n import pick

logger = logging.getLogger(__name__)

_LANGS = {"uz", "ru", "en"}

def _has_playable_lesson():
    """Exists() over tutorial steps that carry a video.

    Both conditions are stated positively — `__gt=""` is true only for a
    non-empty string, and false for NULL. A negated Q across the step
    relation would instead have matched products with *no steps at all*,
    since "no step has an empty video" is vacuously true for them.
    """
    from apps.products.models import ProductTutorialStep

    return Exists(
        ProductTutorialStep.objects.filter(
            Q(video_file_id__gt="") | Q(video_file__gt=""),
            product=OuterRef("pk"),
        )
    )


def _serialize(product: Product, lang: str, request) -> dict:
    photo = None
    if product.photo and product.photo.name:
        photo = request.build_absolute_uri(product.photo.url)
    return {
        "id": product.pk,
        "name": pick(product, "name", lang),
        "description": pick(product, "description", lang),
        "price": product.current_price or None,
        "old_price": product.old_price or None,
        "discount_percent": product.discount_percent,
        "photo": photo,
        "is_top": product.is_top,
        "top_note": pick(product, "top_note", lang) if product.is_top else "",
    }


def _clean_lang(raw: str | None) -> str:
    lang = (raw or "uz").strip().lower()
    return lang if lang in _LANGS else "uz"


def verified_telegram_id(init_data: str) -> int | None:
    """Telegram user id out of a Mini App initData string, or None.

    Returns the id only when the payload's hash matches HMAC-SHA256 over the
    data-check-string with the "WebAppData"-derived secret key — i.e. the
    string really was issued by Telegram for our bot and wasn't tampered with.
    """
    token = getattr(settings, "BOT_TOKEN", "")
    if not token or not init_data or len(init_data) > 4096:
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        their_hash = pairs.pop("hash", "")
        if not their_hash:
            return None
        check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        our_hash = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(our_hash, their_hash):
            return None
        user = json.loads(pairs.get("user", "") or "{}")
        return int(user["id"])
    except (ValueError, KeyError, TypeError):
        return None


class WebAppCatalogView(APIView):
    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        from apps.bot_settings.models import GlobalSettings
        from apps.orders.payments import payments_enabled

        lang = _clean_lang(request.query_params.get("lang"))
        products = (
            Product.objects.filter(is_active=True)
            .order_by("-is_top", "top_order", "name")
        )
        items = [_serialize(p, lang, request) for p in products]

        conf = GlobalSettings.get()
        links = [
            {"kind": kind, "url": url}
            for kind, url in (
                ("instagram", conf.instagram_url),
                ("youtube", conf.youtube_url),
                ("telegram", conf.telegram_url),
            )
            if url
        ]
        return Response(
            {
                "shop": {
                    "name": conf.shop_name,
                    "tagline": pick(conf, "shop_tagline", lang),
                },
                # The Mini App builds t.me deep links (ask a question / open a
                # lesson in the chat) with this — sendData only works for
                # reply-keyboard launches, deep links work from anywhere.
                "bot_username": getattr(settings, "BOT_USERNAME", "") or "",
                # Whether checkout may offer the card option at all.
                "payments_enabled": payments_enabled(),
                "delivery_fees": {
                    "yandex": conf.delivery_fee_yandex,
                    "bts": conf.delivery_fee_bts,
                },
                "links": links,
                "products": items,
                "count": len(items),
            }
        )


class WebAppLessonsView(APIView):
    """The «Darslar» tab: products with their video-lesson steps.

    Only steps that actually carry a video are listed, and only products left
    with at least one of them. A step whose video has not been uploaded yet is
    an empty promise — the tab says "coming soon" instead, and each lesson
    appears by itself the moment its video is added in the panel.

    Personalized to the customer's own products when a *verified* initData is
    supplied; otherwise every product that has a lesson, top ones first.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        lang = _clean_lang(request.query_params.get("lang"))
        telegram_id = verified_telegram_id(
            request.query_params.get("init_data", "")
        )

        playable = Product.objects.filter(is_active=True).filter(
            _has_playable_lesson()
        ).prefetch_related("tutorial_steps")

        products: list[Product] = []
        personalized = False
        if telegram_id:
            products = list(
                playable.filter(
                    userproduct__user__telegram_id=telegram_id
                ).order_by("name")
            )
            personalized = bool(products)
        if not products:
            products = list(playable.order_by("-is_top", "top_order", "name"))

        items = []
        for product in products:
            steps = sorted(
                (s for s in product.tutorial_steps.all() if s.has_video),
                key=lambda s: s.order,
            )
            items.append(
                {
                    "id": product.pk,
                    "name": pick(product, "name", lang),
                    "photo": (
                        request.build_absolute_uri(product.photo.url)
                        if product.photo and product.photo.name
                        else None
                    ),
                    "steps": [
                        {
                            "id": step.pk,
                            "label": pick(step, "button_label", lang),
                            "has_video": True,
                        }
                        for step in steps
                    ],
                }
            )
        return Response(
            {
                "personalized": personalized,
                "bot_username": getattr(settings, "BOT_USERNAME", "") or "",
                "products": items,
                "count": len(items),
            }
        )


class WebAppOrderView(APIView):
    """
    The Mini App's checkout: creates an order for a *verified* customer.

    The only authentication a Mini App has is its initData HMAC, so a valid
    signature is mandatory here — unlike the read-only endpoints above there
    is no anonymous fallback. Prices always come from the database; the client
    only says which product ids and quantities it wants.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    MAX_LINES = 30
    MAX_QTY = 20
    RATE_LIMIT_MAX = 5  # orders per window per customer
    RATE_LIMIT_WINDOW_S = 300

    def post(self, request):
        from apps.orders.models import Order, OrderItem
        from apps.orders.notifications import notify_new_order, request_location
        from apps.users.models import TelegramUser

        data = request.data if isinstance(request.data, dict) else {}
        telegram_id = verified_telegram_id(str(data.get("init_data", "")))
        if telegram_id is None:
            return Response(
                {"detail": "auth"}, status=http_status.HTTP_403_FORBIDDEN
            )
        user = TelegramUser.objects.filter(
            telegram_id=telegram_id,
            is_active=True,
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        ).first()
        if user is None:
            return Response(
                {"detail": "not_registered"}, status=http_status.HTTP_403_FORBIDDEN
            )

        key = f"webapp_order_rl:{telegram_id}"
        if not cache.add(key, 1, self.RATE_LIMIT_WINDOW_S):
            try:
                if cache.incr(key) > self.RATE_LIMIT_MAX:
                    return Response(
                        {"detail": "rate_limited"},
                        status=http_status.HTTP_429_TOO_MANY_REQUESTS,
                    )
            except ValueError:
                cache.set(key, 1, self.RATE_LIMIT_WINDOW_S)

        delivery = str(data.get("delivery", ""))
        if delivery not in Order.Delivery.values:
            return Response(
                {"detail": "delivery"}, status=http_status.HTTP_400_BAD_REQUEST
            )
        address = str(data.get("address", "")).strip()[:1000]
        if len(address) < 5:
            return Response(
                {"detail": "address"}, status=http_status.HTTP_400_BAD_REQUEST
            )
        comment = str(data.get("comment", "")).strip()[:1000]

        from apps.bot_settings.models import GlobalSettings
        from apps.orders.payments import (
            MAX_INVOICE_SOM,
            MIN_INVOICE_SOM,
            can_invoice,
            payments_enabled,
            send_invoice,
        )

        phone = TelegramUser.normalize_phone(str(data.get("phone", "")).strip())
        phone = phone or user.phone_number
        if not phone:
            return Response(
                {"detail": "phone"}, status=http_status.HTTP_400_BAD_REQUEST
            )

        raw_items = data.get("items")
        if not isinstance(raw_items, list) or not raw_items:
            return Response(
                {"detail": "items"}, status=http_status.HTTP_400_BAD_REQUEST
            )
        wanted: dict[int, int] = {}
        for entry in raw_items[: self.MAX_LINES]:
            try:
                product_id = int(entry.get("id"))
                quantity = int(entry.get("qty"))
            except (AttributeError, TypeError, ValueError):
                continue
            if quantity < 1:
                continue
            wanted[product_id] = min(quantity, self.MAX_QTY)
        products = {
            p.pk: p
            for p in Product.objects.filter(pk__in=wanted, is_active=True)
        }
        lines = [
            (products[pid], qty) for pid, qty in wanted.items() if pid in products
        ]
        if not lines:
            return Response(
                {"detail": "items"}, status=http_status.HTTP_400_BAD_REQUEST
            )
        # A product the shop hasn't priced yet cannot be sold: letting it
        # through would bill the customer for delivery alone.
        if any(product.current_price <= 0 for product, _ in lines):
            return Response(
                {"detail": "unpriced"}, status=http_status.HTTP_400_BAD_REQUEST
            )

        conf = GlobalSettings.get()
        delivery_fee = (
            conf.delivery_fee_yandex
            if delivery == Order.Delivery.YANDEX
            else conf.delivery_fee_bts
        )
        total = sum(p.current_price * qty for p, qty in lines) + delivery_fee

        # Neither carrier collects money — a Yandex courier only carries, and
        # the shop has no BTS cash-collection contract — so the customer pays
        # up front by card. The cash fallback exists for one case only: the
        # provider token being missing or broken, where a shop that can take
        # no orders at all would be worse than an operator ringing to arrange
        # payment. An amount Telegram won't invoice is refused outright.
        if payments_enabled() and not can_invoice(total):
            return Response(
                {
                    "detail": "amount",
                    "min": MIN_INVOICE_SOM,
                    "max": MAX_INVOICE_SOM,
                },
                status=http_status.HTTP_400_BAD_REQUEST,
            )
        payment_method = (
            Order.PaymentMethod.ONLINE
            if payments_enabled()
            else Order.PaymentMethod.COD
        )

        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                customer_name=user.full_name or str(telegram_id),
                phone_number=phone,
                delivery_method=delivery,
                address=address,
                comment=comment,
                payment_method=payment_method,
                delivery_fee=delivery_fee,
                total=total,
            )
            OrderItem.objects.bulk_create(
                OrderItem(
                    order=order,
                    product=product,
                    product_name=product.name,
                    price=product.current_price,
                    quantity=qty,
                )
                for product, qty in lines
            )

        try:
            notify_new_order(order)
        except Exception:  # noqa: BLE001 — the order is saved; sends are extra
            logger.exception("Order %s: notification crashed", order.pk)

        invoiced = False
        if payment_method == Order.PaymentMethod.ONLINE:
            try:
                invoiced = send_invoice(order)
            except Exception:  # noqa: BLE001 — same: never lose a saved order
                logger.exception("Order %s: invoice crashed", order.pk)

        # A Yandex courier needs a point on the map — but asking for it now
        # would be a third message on top of the confirmation and the invoice,
        # for a courier nobody dispatches until the money arrives. So the ask
        # normally follows the payment (see bot/handlers/payments.py); it only
        # happens here when there is no invoice coming at all.
        if (
            order.delivery_method == Order.Delivery.YANDEX
            and payment_method == Order.PaymentMethod.COD
        ):
            try:
                request_location(order)
            except Exception:  # noqa: BLE001
                logger.exception("Order %s: location request crashed", order.pk)

        return Response(
            {
                "ok": True,
                "order_id": order.pk,
                "total": order.total,
                "delivery_fee": order.delivery_fee,
                "payment": payment_method,
                "invoice_sent": invoiced,
            }
        )
