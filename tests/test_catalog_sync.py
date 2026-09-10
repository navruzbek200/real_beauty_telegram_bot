"""
Tests for `manage.py sync_catalog`.

The command runs unattended on every deploy, so the property that matters most
is what it *doesn't* do: never overwrite a description or a photo the shop has
already put in, and never touch a price. The rest is the happy path — new
products appear with all three languages and their studio shot attached.
"""

from __future__ import annotations

from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from apps.products.catalog import CATALOG
from apps.products.models import Product

ASSETS = Path(__file__).resolve().parents[1] / "apps" / "products" / "assets" / "catalog"


class CatalogDataTests(TestCase):
    def test_names_are_unique(self):
        names = [e["name"] for e in CATALOG]
        self.assertEqual(len(names), len(set(names)), "duplicate product name")

    def test_every_referenced_photo_exists(self):
        missing = [
            e["photo"]
            for e in CATALOG
            if e.get("photo") and not (ASSETS / f"{e['photo']}.jpg").exists()
        ]
        self.assertEqual(missing, [])

    def test_new_products_carry_all_three_languages(self):
        """An entry the database can't already have must be complete.

        Entries without Uzbek text describe rows that already exist (the shop
        wrote their Uzbek copy in the panel); those only add ru/en. But an
        entry that *creates* a product has to bring every language, or the
        catalogue ships a card that is blank in two of the shop's languages.
        """
        for entry in CATALOG:
            if not entry.get("uz"):
                continue
            with self.subTest(product=entry["name"]):
                self.assertTrue(entry.get("ru"), "missing ru")
                self.assertTrue(entry.get("en"), "missing en")


class SyncCatalogTests(TestCase):
    def _run(self, **opts) -> str:
        out = StringIO()
        call_command("sync_catalog", stdout=out, stderr=StringIO(), **opts)
        return out.getvalue()

    def _first_creatable(self) -> dict:
        return next(e for e in CATALOG if e.get("uz") and e.get("photo"))

    def test_creates_products_with_photo_and_translations(self):
        self._run()
        entry = self._first_creatable()
        product = Product.objects.get(name=entry["name"])
        self.assertEqual(product.description, entry["uz"])
        self.assertEqual(product.description_ru, entry["ru"])
        self.assertEqual(product.description_en, entry["en"])
        self.assertTrue(product.photo.name.endswith(".jpg"))
        self.assertTrue(product.photo.size > 0)

    def test_is_idempotent(self):
        self._run()
        count = Product.objects.count()
        self.assertEqual(count, len({e["name"] for e in CATALOG if e.get("uz")}))
        second = self._run()
        self.assertIn("0 new, 0 updated, 0 photo(s)", second)
        self.assertEqual(Product.objects.count(), count)

    def test_fills_translations_and_photo_of_an_existing_product(self):
        entry = next(e for e in CATALOG if e.get("photo") and not e.get("uz"))
        product = Product.objects.create(
            name=entry["name"], description="Do'kon yozgan matn", current_price=99_000
        )
        self._run()
        product.refresh_from_db()
        self.assertEqual(product.description, "Do'kon yozgan matn")  # untouched
        self.assertEqual(product.description_ru, entry["ru"])
        self.assertEqual(product.current_price, 99_000)  # prices are never synced
        self.assertTrue(product.photo.name)

    def test_never_overwrites_what_the_shop_already_wrote(self):
        entry = self._first_creatable()
        product = Product.objects.create(
            name=entry["name"],
            description="qo'lda",
            description_ru="вручную",
            description_en="by hand",
            photo="products/shop-upload.jpg",
        )
        self._run()
        product.refresh_from_db()
        self.assertEqual(product.description_ru, "вручную")
        self.assertEqual(product.description_en, "by hand")
        self.assertEqual(product.photo.name, "products/shop-upload.jpg")

    def test_force_photo_replaces_an_existing_one(self):
        entry = self._first_creatable()
        product = Product.objects.create(
            name=entry["name"], description="x", photo="products/shop-upload.jpg"
        )
        self._run(force_photo=True)
        product.refresh_from_db()
        self.assertNotEqual(product.photo.name, "products/shop-upload.jpg")

    def test_dry_run_writes_nothing(self):
        out = self._run(dry_run=True)
        self.assertIn("Would apply", out)
        self.assertEqual(Product.objects.count(), 0)
