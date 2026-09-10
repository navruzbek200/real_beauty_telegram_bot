"""
Fill the catalogue with a realistic, ready-to-demo skincare line: products with
descriptions and prices, some marked "top of the month" with a discount, and
multi-step video lessons attached (a couple of steps deliberately have no intro
text, to show that field is optional). Idempotent — safe to re-run, and safe on
production: it only touches products and their lessons, never customers.

    python manage.py seed_showcase
"""

from __future__ import annotations

import io
from typing import Any

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.products.models import Product, ProductTutorialStep

# Deliberately mismatched dimensions — portrait, landscape, tiny, huge — so a
# seeded catalogue proves the Mini App's `object-fit: cover` grid normalises any
# upload into a clean, equal-sized card. "biri kichik biri sig'may qolgan" was
# the complaint; this is the regression fixture for it.
_SIZES = [(600, 800), (900, 500), (300, 300), (1200, 900), (500, 700), (800, 800)]
_PALETTE = [
    ((255, 228, 225), (255, 182, 193)),  # rose
    ((224, 242, 241), (128, 203, 196)),  # mint
    ((255, 243, 224), (255, 204, 128)),  # amber
    ((237, 231, 246), (179, 157, 219)),  # lavender
    ((232, 245, 233), (129, 199, 132)),  # green
    ((225, 245, 254), (129, 212, 250)),  # sky
]


def _placeholder_image(name: str, index: int) -> ContentFile:
    """A clean branded gradient card with the product's initial — a stand-in
    until real photos are added, generated at a deliberately odd size."""
    from PIL import Image, ImageDraw

    w, h = _SIZES[index % len(_SIZES)]
    top, bottom = _PALETTE[index % len(_PALETTE)]
    img = Image.new("RGB", (w, h), top)
    draw = ImageDraw.Draw(img)
    for y in range(h):  # vertical gradient
        f = y / max(1, h - 1)
        draw.line(
            [(0, y), (w, y)],
            fill=tuple(round(top[c] + (bottom[c] - top[c]) * f) for c in range(3)),
        )
    # A soft "bottle" silhouette + the product initial, centred — no font files
    # needed beyond PIL's bundled default, so it renders the same on any host.
    cx, cy = w / 2, h / 2
    r = min(w, h) * 0.26
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255))
    letter = next((c for c in name if c.isalnum()), "R").upper()
    try:
        from PIL import ImageFont

        font = ImageFont.load_default(size=int(r))
    except Exception:  # noqa: BLE001 — older Pillow: default font has no size arg
        font = None
    box = draw.textbbox((0, 0), letter, font=font)
    draw.text(
        (cx - (box[2] - box[0]) / 2, cy - (box[3] - box[1]) / 2 - box[1]),
        letter,
        fill=(120, 95, 110),
        font=font,
    )
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return ContentFile(buf.getvalue())

# name, description, price, old_price, top_order(0=not top), top_note, steps
# steps: list of (button_label, intro_text)  — intro_text "" means "optional, left blank"
CATALOGUE: list[dict[str, Any]] = [
    {
        "name": "Vitamin C Serum ✨",
        "description": (
            "Teriga yorqinlik beruvchi C vitaminli serum. Dog'larni "
            "oqartiradi, teri rangini tenglashtiradi. Ertalab, SPF'dan oldin."
        ),
        "price": 149000,
        "old_price": 199000,
        "top": 1,
        "top_note": "🔥 Eng ko'p sotilgan",
        "steps": [
            ("1-qadam: Tozalash", "Yuzni yumshoq ko'pik bilan yuving va quriting."),
            ("2-qadam: Serum surtish", "3-4 tomchi serumni yuzga teng yoying."),
            ("3-qadam: Namlash", ""),
        ],
    },
    {
        "name": "Tungi tiklovchi krem 🌙",
        "description": (
            "Uyqu paytida terini tiklaydi va namlaydi. Retinol va seramid "
            "bilan. Kechqurun, tozalangan teriga."
        ),
        "price": 189000,
        "old_price": None,
        "top": 2,
        "top_note": "🌙 Tunggi parvarish",
        "steps": [
            ("1-qadam: Tayyorlash", "Toner bilan terini tayyorlang."),
            ("2-qadam: Krem", ""),
        ],
    },
    {
        "name": "SPF 50 Quyoshdan himoya ☀️",
        "description": (
            "Har kunlik yengil quyoshdan himoya. Oq iz qoldirmaydi, "
            "makiyaj ostiga mos. UVA/UVB himoya."
        ),
        "price": 129000,
        "old_price": 159000,
        "top": 3,
        "top_note": "☀️ Har kuni shart",
        "steps": [
            ("Qanday surtiladi", "Parvarishning eng oxirida, chiqishdan 15 daqiqa oldin."),
        ],
    },
    {
        "name": "Hyaluron namlovchi toner 💧",
        "description": (
            "Gialuron kislotali toner terini chuqur namlaydi va keyingi "
            "vositalarni yaxshiroq singdiradi."
        ),
        "price": 89000,
        "old_price": None,
        "top": 0,
        "top_note": "",
        "steps": [
            ("Ishlatish tartibi", "Tozalashdan keyin paxta yoki kaft bilan surting."),
        ],
    },
    {
        "name": "Niasinamid tekislovchi serum 🧴",
        "description": (
            "Yog' balansini tartibga soladi, teshiklarni toraytiradi. "
            "Yog'li va aralash teri uchun ideal."
        ),
        "price": 119000,
        "old_price": 139000,
        "top": 0,
        "top_note": "",
        "steps": [],  # a product with no lessons yet — bot says "coming soon"
    },
    {
        "name": "Yumshoq tozalovchi ko'pik 🫧",
        "description": (
            "Kunlik yumshoq ko'pik terini quritmasdan tozalaydi. "
            "Barcha teri turlari uchun."
        ),
        "price": 69000,
        "old_price": None,
        "top": 0,
        "top_note": "",
        "steps": [
            ("1-qadam: Ho'llash", "Yuzni iliq suv bilan ho'llang."),
            ("2-qadam: Ko'piklash", "Bir oz ko'pikni kaftda ko'piklab yuzga surting."),
            ("3-qadam: Yuvish", ""),
        ],
    },
]


class Command(BaseCommand):
    help = "Seed a realistic demo catalogue (products + lessons + top picks)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--no-images",
            action="store_true",
            help="Skip generating placeholder product images.",
        )
        parser.add_argument(
            "--with-lessons",
            action="store_true",
            help=(
                "Also seed tutorial steps. Off by default: they carry no video, "
                "so customers never see them and they only clutter the panel."
            ),
        )

    def handle(self, *args: Any, **opts: Any) -> None:
        for index, item in enumerate(CATALOGUE):
            product, _ = Product.objects.update_or_create(
                name=item["name"],
                defaults={
                    "description": item["description"],
                    "current_price": item["price"],
                    "old_price": item["old_price"],
                    "is_active": True,
                    "is_top": bool(item["top"]),
                    "top_order": item["top"] or 1,
                    "top_note": item["top_note"],
                },
            )
            if not opts["no_images"]:
                # Replace so re-runs don't pile up orphaned files.
                product.photo.delete(save=False)
                product.photo.save(
                    f"demo_{product.pk}.jpg",
                    _placeholder_image(item["name"], index),
                    save=True,
                )
            # Lesson rows are only seeded on request. A step with no video is
            # invisible to customers by design (see WebAppLessonsView), so
            # seeding them onto a live shop just puts rows in the panel that
            # nobody can watch — exactly the "fake lessons" this command used
            # to leave behind.
            product.tutorial_steps.all().delete()
            steps = 0
            if opts["with_lessons"]:
                for order, (label, intro) in enumerate(item["steps"], start=1):
                    ProductTutorialStep.objects.create(
                        product=product,
                        order=order,
                        button_label=label,
                        intro_text=intro,
                    )
                steps = len(item["steps"])
            top = "TOP" if item["top"] else "—"
            img = "—" if opts["no_images"] else "🖼"
            self.stdout.write(f"• {item['name']} [{top}] · {steps} dars {img}")

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ {len(CATALOGUE)} ta namuna mahsulot tayyor "
                "(top + chegirmalar bilan)."
            )
        )
