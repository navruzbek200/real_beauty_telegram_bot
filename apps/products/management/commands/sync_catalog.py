"""
Bring the database in line with `apps/products/catalog/` — the shop's real
product list, its studio photos and their uz/ru/en descriptions.

    python manage.py sync_catalog
    python manage.py sync_catalog --dry-run     # show what would change
    python manage.py sync_catalog --force-photo # re-upload photos too

Safe to run on every deploy. It only *fills* — a description the shop has
already written, a photo it has already uploaded and every price stay exactly
as they are, because this command runs unattended and silently reverting the
shop's own edits would be worse than a missing translation.

Products are matched on `name`, so renaming a product in the admin panel makes
the next run create it again — rename here too, or leave the name alone.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.products.catalog import CATALOG
from apps.products.models import Product

# …/apps/products/management/commands/sync_catalog.py → …/apps/products
ASSETS = Path(__file__).resolve().parents[2] / "assets" / "catalog"


class Command(BaseCommand):
    help = "Sync products, photos and uz/ru/en descriptions from the catalogue."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report the changes without writing anything.",
        )
        parser.add_argument(
            "--force-photo",
            action="store_true",
            help="Replace photos that are already set (default: only fill empty).",
        )

    def handle(self, *args: Any, **opts: Any) -> None:
        dry, force_photo = opts["dry_run"], opts["force_photo"]
        created = updated = photos = skipped = 0
        missing_assets: list[str] = []

        for entry in CATALOG:
            name = entry["name"]
            product = Product.objects.filter(name=name).first()
            changes: list[str] = []

            if product is None:
                if not entry.get("uz"):
                    # An entry with no Uzbek text describes a product that is
                    # expected to exist already; creating it empty would put a
                    # blank card in the shop.
                    self.stderr.write(f"  ! missing and has no uz text: {name}")
                    skipped += 1
                    continue
                product = Product(name=name, is_active=True)
                changes.append("new")

            for lang_key, field in (
                ("uz", "description"),
                ("ru", "description_ru"),
                ("en", "description_en"),
                # Only for names that carry an Uzbek word ("5 dona", "BB krem");
                # a plain Latin product name reads the same in all three and is
                # left without a translation on purpose.
                ("name_ru", "name_ru"),
                ("name_en", "name_en"),
            ):
                text = entry.get(lang_key)
                if text and not getattr(product, field):
                    setattr(product, field, text)
                    changes.append(field)

            photo_name = entry.get("photo")
            wants_photo = photo_name and (
                force_photo or not (product.photo and product.photo.name)
            )
            asset = ASSETS / f"{photo_name}.jpg" if photo_name else None
            if wants_photo and asset and not asset.exists():
                missing_assets.append(asset.name)
                wants_photo = False

            if not changes and not wants_photo:
                continue

            if dry:
                mark = "+" if "new" in changes else "~"
                bits = [c for c in changes if c != "new"]
                if wants_photo:
                    bits.append("photo")
                self.stdout.write(f"  {mark} {name} → {', '.join(bits) or 'create'}")
                created += "new" in changes
                updated += "new" not in changes
                photos += bool(wants_photo)
                continue

            product.save()
            if "new" in changes:
                created += 1
            else:
                updated += 1
            if wants_photo and asset:
                product.photo.save(
                    f"{photo_name}.jpg",
                    ContentFile(asset.read_bytes()),
                    save=True,
                )
                photos += 1

        if missing_assets:
            self.stderr.write(
                self.style.WARNING(
                    f"⚠ {len(missing_assets)} photo file(s) not found in "
                    f"{ASSETS}: {', '.join(sorted(set(missing_assets)))}"
                )
            )
        head = "Would apply" if dry else "Applied"
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ {head}: {created} new, {updated} updated, {photos} photo(s). "
                f"Catalogue holds {len(CATALOG)} entries, "
                f"database holds {Product.objects.count()} products."
            )
        )
        if skipped:
            self.stdout.write(f"   {skipped} entr(ies) skipped — see warnings above.")
