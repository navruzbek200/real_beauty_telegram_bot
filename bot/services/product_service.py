from __future__ import annotations

from asgiref.sync import sync_to_async
from django.db.models import Exists, OuterRef, Q

from apps.products.models import Product, ProductTutorialStep


def _has_playable_lesson():
    """Exists() over tutorial steps that carry a video.

    Stated positively on purpose — `__gt=""` matches a non-empty string and
    never NULL. Negating across the step relation would have matched products
    with no steps at all, since "no step has an empty video" holds vacuously.
    """
    return Exists(
        ProductTutorialStep.objects.filter(
            Q(video_file_id__gt="") | Q(video_file__gt=""),
            product=OuterRef("pk"),
        )
    )


@sync_to_async
def get_active_products() -> list[Product]:
    return list(Product.objects.filter(is_active=True))


@sync_to_async
def get_active_products_page(offset: int, limit: int) -> tuple[list[Product], int]:
    """One page of the catalogue plus the full count, in a single round trip.

    LIMIT/OFFSET at the database keeps the catalogue answer cheap no matter how
    many products the shop ends up with — the whole point of paginating instead
    of shipping one card per product.
    """
    qs = Product.objects.filter(is_active=True).order_by("name")
    total = qs.count()
    return list(qs[offset : offset + limit]), total


@sync_to_async
def get_top_products() -> list[Product]:
    """
    This month's curated top list.

    Deactivated products are filtered out even when still flagged as top: the
    shop switches a product off when it stops selling it, and forgetting to
    untick the top flag must not keep advertising it.
    """
    return list(
        Product.objects.filter(is_top=True, is_active=True).order_by(
            "top_order", "name"
        )
    )


@sync_to_async
def get_product(product_id: int) -> Product | None:
    return Product.objects.filter(pk=product_id).first()


@sync_to_async
def get_tutorial_products(telegram_id: int) -> list[Product]:
    """Products with a lesson the customer can actually watch.

    Only products holding at least one step with an uploaded video count. A
    step whose video is still missing would open onto "coming soon", which
    reads as a broken section rather than an honest one — better to say
    nothing is ready yet and let each lesson appear as its video is added.

    Their own purchases come first; failing that, everything that has a
    lesson, so a brand-new customer still has something to watch.
    """
    playable = Product.objects.filter(is_active=True).filter(_has_playable_lesson())

    owned = list(
        playable.filter(userproduct__user__telegram_id=telegram_id)
        .distinct()
        .order_by("name")
    )
    if owned:
        return owned
    return list(playable.order_by("-is_top", "top_order", "name"))


@sync_to_async
def get_tutorial_steps(product_id: int) -> list[ProductTutorialStep]:
    return list(
        ProductTutorialStep.objects.filter(product_id=product_id).order_by("order")
    )


@sync_to_async
def get_tutorial_step(step_id: int) -> ProductTutorialStep | None:
    return (
        ProductTutorialStep.objects.select_related("product")
        .filter(pk=step_id)
        .first()
    )


@sync_to_async
def cache_video_file_id(step_id: int, file_id: str) -> None:
    """Persist the Telegram file_id after the first upload send (reuse later)."""
    ProductTutorialStep.objects.filter(pk=step_id).update(video_file_id=file_id)
