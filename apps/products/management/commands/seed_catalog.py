"""
Load the real erste Liebe / MERIKIT / Dr.G catalogue the shop sent, with proper
names, bilingual descriptions, prices and a few discounts / top picks. Each
product gets a clean, brand-coloured placeholder image so the catalogue looks
finished immediately; the shop replaces those with real photos in the admin
(the attached photos can't be pulled in from here).

    python manage.py seed_catalog            # add / update the products
    python manage.py seed_catalog --replace  # + deactivate the old demo items

Idempotent, matched on name.
"""

from __future__ import annotations

import io
import textwrap
from typing import Any

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.products.models import Product

# name, brand, desc_uz, desc_en, price, old_price, top_order(0=no), top_note,
# (top_color, bottom_color) for the placeholder gradient
CATALOG: list[dict[str, Any]] = [
    {
        "name": "Low pH Madeca Green Creamy Biome Cleansing Foam",
        "brand": "erste Liebe",
        "desc_uz": (
            "Past pH li yumshoq tozalovchi ko'pik. 0.5% salitsil kislota va "
            "organik yuvuvchi moddalar teshiklarni ta'sirsiz tozalaydi, ortiqcha "
            "yog' va changni ketkazadi. Poliol teri namlik to'sig'ini saqlaydi.\n\n"
            "Yog'li va muammoli teri uchun · 150 ml"
        ),
        "desc_en": (
            "Hypoallergenic coconut pore cleanser with 0.5% salicylic acid. Sebum "
            "control & acne relief, deeply cleanses pores without irritation."
        ),
        "price": 95000,
        "old_price": 119000,
        "top": 1,
        "top_note": "🔥 Yog'li teri uchun tanlov",
        "colors": ((196, 224, 184), (150, 196, 140)),
    },
    {
        "name": "Madeca White Creamy Biome Cleansing Foam",
        "brand": "erste Liebe",
        "desc_uz": (
            "Sezgir teri uchun namlantiruvchi krem-ko'pik. Madekassosid, salitsil "
            "kislota va Biome kompleksi terini tinchlantiradi. Yuvingandan keyin "
            "ham teri namligini saqlaydi.\n\nSezgir teri uchun · 150 ml"
        ),
        "desc_en": (
            "Whipping cream cleanser for sensitive skin. Madecassoside, salicylic "
            "acid and Biome complex soothe skin; stays moisturized after cleansing."
        ),
        "price": 105000,
        "old_price": None,
        "top": 0,
        "top_note": "",
        "colors": ((245, 243, 238), (225, 221, 212)),
    },
    {
        "name": "pH Cleansing R.E.D Blemish Clear Soothing Foam",
        "brand": "Dr.G",
        "desc_uz": (
            "pH balansini saqlovchi tinchlantiruvchi ko'pik. 5-CICA kompleksi "
            "qizarish va yallig'lanishni kamaytiradi, muammoli terini yumshatadi.\n\n"
            "Qizargan, sezgir teri uchun · 150 ml"
        ),
        "desc_en": (
            "pH balancing soothing foam with 5-CICA complex. Calms redness and "
            "blemish-prone skin."
        ),
        "price": 120000,
        "old_price": 145000,
        "top": 2,
        "top_note": "✨ Qizarishga qarshi",
        "colors": ((178, 223, 213), (120, 200, 185)),
    },
    {
        "name": "O2 Mask Cleanser",
        "brand": "MERIKIT",
        "desc_uz": (
            "Kislorodli ko'pik-niqob tozalovchi. Teshiklarni chuqur tozalaydi va "
            "teriga tozalik hissini beradi. Tabiat va ilm uyg'unligi.\n\n"
            "Barcha teri turlari uchun"
        ),
        "desc_en": "Oxygen mask cleanser — deep pore cleansing, fresh finish.",
        "price": 85000,
        "old_price": None,
        "top": 0,
        "top_note": "",
        "colors": ((235, 242, 250), (205, 222, 240)),
    },
    {
        "name": "Double Peeling Gel",
        "brand": "MERIKIT",
        "desc_uz": (
            "Ikki bosqichli pilling geli. O'lik hujayralarni yumshoq tozalaydi, "
            "terini silliq va yorqin qiladi. Haftada 1–2 marta.\n\n"
            "Barcha teri turlari uchun"
        ),
        "desc_en": "Double peeling gel — gently removes dead skin for smooth, bright skin.",
        "price": 110000,
        "old_price": None,
        "top": 0,
        "top_note": "",
        "colors": ((250, 244, 214), (240, 224, 160)),
    },
    {
        "name": "One Point Cleansing Oil",
        "brand": "MERIKIT",
        "desc_uz": (
            "Makiyaj va yog'li iflosliklarni eritadigan tozalovchi moy. Suv bilan "
            "yengil yuviladi, terini quritmaydi.\n\nBarcha teri turlari uchun"
        ),
        "desc_en": "Cleansing oil — melts makeup and sebum, rinses clean without drying.",
        "price": 90000,
        "old_price": None,
        "top": 0,
        "top_note": "",
        "colors": ((214, 240, 236), (168, 214, 208)),
    },
    {
        "name": "Grain Rice Foam",
        "brand": "MERIKIT",
        "desc_uz": (
            "Guruch ekstraktli tozalovchi ko'pik. Terini yumshoq tozalaydi va "
            "oziqlantiradi, tabiiy yorqinlik beradi.\n\nQuruq va normal teri uchun"
        ),
        "desc_en": "Rice grain cleansing foam — gentle cleansing with a natural glow.",
        "price": 65000,
        "old_price": 79000,
        "top": 0,
        "top_note": "",
        "colors": ((250, 238, 205), (236, 214, 150)),
    },
    {
        "name": "Rose Waterproof Lip & Eye Remover",
        "brand": "MERIKIT",
        "desc_uz": (
            "Suvga chidamli makiyaj uchun ikki fazali lab va ko'z tozalovchisi. "
            "Ta'sirsiz, nozik teriga mos.\n\nBarcha teri turlari uchun"
        ),
        "desc_en": "Two-phase waterproof lip & eye makeup remover, gentle on delicate skin.",
        "price": 55000,
        "old_price": None,
        "top": 0,
        "top_note": "",
        "colors": ((246, 244, 245), (222, 218, 222)),
    },
    {
        "name": "Cica Perfect Sun Cream SPF50+ PA++++",
        "brand": "MERIKIT",
        "desc_uz": (
            "Cica tarkibli quyoshdan himoya kremi. UVA va UVB nurlaridan himoya "
            "qiladi, terini tinchlantiradi. Har kunlik foydalanish uchun.\n\n"
            "SPF50+ / PA++++ · barcha teri turlari"
        ),
        "desc_en": (
            "Cica sun cream SPF50+/PA++++. Protects from UVA/UVB, calms and keeps "
            "skin healthy."
        ),
        "price": 130000,
        "old_price": 165000,
        "top": 3,
        "top_note": "☀️ Har kuni shart",
        "colors": ((224, 240, 224), (176, 214, 180)),
    },
    {
        "name": "Multi Protection Balm SPF37 PA++",
        "brand": "MERIKIT",
        "desc_uz": (
            "Ko'p vazifali himoya balzami. UVA va UVB nurlaridan himoya qiladi, "
            "terini tekislaydi va tinchlantiradi.\n\nSPF37 / PA++ · barcha teri turlari"
        ),
        "desc_en": "Multi protection balm SPF37/PA++. UVA/UVB protection with a smoothing finish.",
        "price": 140000,
        "old_price": None,
        "top": 0,
        "top_note": "",
        "colors": ((248, 232, 240), (236, 190, 214)),
    },
]


def _placeholder(brand: str, name: str, colors) -> ContentFile:
    """A clean branded gradient card: brand on top, wrapped product name, at a
    fixed portrait ratio so every card in the grid matches."""
    from PIL import Image, ImageDraw, ImageFont

    w, h = 900, 900
    top, bottom = colors
    img = Image.new("RGB", (w, h), top)
    draw = ImageDraw.Draw(img)
    for y in range(h):
        f = y / (h - 1)
        draw.line(
            [(0, y), (w, y)],
            fill=tuple(round(top[c] + (bottom[c] - top[c]) * f) for c in range(3)),
        )
    # soft rounded "label" panel
    pad = 90
    draw.rounded_rectangle(
        [pad, pad, w - pad, h - pad], radius=48, fill=(255, 255, 255, 0),
        outline=(255, 255, 255), width=6,
    )

    def font(size: int):
        try:
            return ImageFont.load_default(size=size)
        except Exception:  # noqa: BLE001 — very old Pillow
            return ImageFont.load_default()

    ink = (70, 60, 66)
    brand_f, name_f = font(46), font(58)
    draw.text((w / 2, 210), brand.upper(), font=brand_f, fill=ink, anchor="mm")
    lines = textwrap.wrap(name, width=16)[:4]
    y = h / 2 - (len(lines) - 1) * 40
    for line in lines:
        draw.text((w / 2, y), line, font=name_f, fill=ink, anchor="mm")
        y += 80
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return ContentFile(buf.getvalue())


class Command(BaseCommand):
    help = "Seed the real erste Liebe / MERIKIT / Dr.G product catalogue."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--no-images", action="store_true")
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Deactivate the old demo/placeholder products first.",
        )

    def handle(self, *args: Any, **opts: Any) -> None:
        if opts["replace"]:
            demo_names = [
                "Vitamin C Serum ✨", "Tungi tiklovchi krem 🌙",
                "SPF 50 Quyoshdan himoya ☀️", "Hyaluron namlovchi toner 💧",
                "Niasinamid tekislovchi serum 🧴", "Yumshoq tozalovchi ko'pik 🫧",
                "serum", "toner", "spf",
                "Real Beauty Vitamin C Serum", "Real Beauty Night Cream",
            ]
            n = Product.objects.filter(name__in=demo_names).update(is_active=False)
            self.stdout.write(f"• {n} ta eski/demo mahsulot o'chirildi (yashirildi)")

        for item in CATALOG:
            full_name = f"{item['brand']} — {item['name']}"
            product, _ = Product.objects.update_or_create(
                name=full_name,
                defaults={
                    "name_en": full_name,
                    "description": item["desc_uz"],
                    "description_en": item["desc_en"],
                    "current_price": item["price"],
                    "old_price": item["old_price"],
                    "is_active": True,
                    "is_top": bool(item["top"]),
                    "top_order": item["top"] or 1,
                    "top_note": item["top_note"],
                },
            )
            if not opts["no_images"]:
                product.photo.delete(save=False)
                product.photo.save(
                    f"catalog_{product.pk}.jpg",
                    _placeholder(item["brand"], item["name"], item["colors"]),
                    save=True,
                )
            self.stdout.write(f"• {full_name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ {len(CATALOG)} ta mahsulot qo'shildi. Real rasmlarni admin "
                "paneldan yuklang."
            )
        )
