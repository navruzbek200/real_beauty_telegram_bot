from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from apps.products.models import Product


class TopProductApiTests(APITestCase):
    """
    The Top Products CRM page needs full control from its own screen: add,
    edit, reorder, remove — without a trip through the main catalogue.
    """

    def setUp(self):
        self.client = APIClient()
        user = get_user_model().objects.create_superuser("owner", "o@example.com", "pw")
        self.client.force_authenticate(user)

    def test_creating_here_lands_the_product_in_the_top_list(self):
        response = self.client.post(
            "/api/v1/top-products/",
            {"name": "Yangi seruma", "current_price": 120_000},
        )
        self.assertEqual(response.status_code, 201, response.data)
        product = Product.objects.get(pk=response.data["id"])
        self.assertTrue(product.is_top)
        self.assertEqual(product.current_price, 120_000)

    def test_a_new_entry_is_active_by_default(self):
        # The create form has no is_active field; a multipart POST missing it
        # must not silently create an invisible, deactivated product.
        response = self.client.post(
            "/api/v1/top-products/", {"name": "Yangi", "current_price": 1}
        )
        self.assertTrue(Product.objects.get(pk=response.data["id"]).is_active)

    def test_new_entries_append_after_the_existing_top_order(self):
        Product.objects.create(name="Birinchi", is_top=True, top_order=5)
        response = self.client.post("/api/v1/top-products/", {"name": "Ikkinchi"})
        self.assertEqual(response.data["top_order"], 6)

    def test_discount_percent_is_computed_from_both_prices(self):
        response = self.client.post(
            "/api/v1/top-products/",
            {"name": "Chegirmali", "current_price": 80_000, "old_price": 100_000},
        )
        self.assertEqual(response.data["discount_percent"], 20)

    def test_deleting_clears_the_top_flag_without_dropping_the_product(self):
        product = Product.objects.create(name="Krem", is_top=True, top_order=1)
        response = self.client.delete(f"/api/v1/top-products/{product.pk}/")
        self.assertEqual(response.status_code, 204)
        product.refresh_from_db()
        self.assertFalse(product.is_top)  # still exists — purchase history intact

    def test_reorder_sets_top_order_from_list_position(self):
        first = Product.objects.create(name="A", is_top=True, top_order=1)
        second = Product.objects.create(name="B", is_top=True, top_order=2)
        third = Product.objects.create(name="C", is_top=True, top_order=3)

        response = self.client.post(
            "/api/v1/top-products/reorder/",
            {"ids": [third.pk, first.pk, second.pk]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["updated"], 3)

        first.refresh_from_db()
        second.refresh_from_db()
        third.refresh_from_db()
        self.assertEqual(third.top_order, 1)
        self.assertEqual(first.top_order, 2)
        self.assertEqual(second.top_order, 3)

    def test_reorder_ignores_ids_that_are_not_in_the_top_list(self):
        outside = Product.objects.create(name="Topda emas", is_top=False)
        response = self.client.post(
            "/api/v1/top-products/reorder/", {"ids": [outside.pk]}
        )
        self.assertEqual(response.data["updated"], 0)
        outside.refresh_from_db()
        self.assertFalse(outside.is_top)


class WebAppCatalogTests(APITestCase):
    """The Mini App catalogue is public, read-only and localized."""

    def test_catalog_is_public_and_lists_active_products(self):
        from apps.products.models import Product

        Product.objects.create(name="Serum", current_price=100, is_active=True)
        Product.objects.create(name="Yashirin", is_active=False)

        # No auth on purpose — it's a shopfront.
        response = self.client.get("/api/v1/webapp/catalog/?lang=uz")
        self.assertEqual(response.status_code, 200)
        names = [p["name"] for p in response.data["products"]]
        self.assertIn("Serum", names)
        self.assertNotIn("Yashirin", names)

    def test_catalog_localizes_names(self):
        from apps.products.models import Product

        Product.objects.create(name="Krem", name_ru="Крем", current_price=1)
        response = self.client.get("/api/v1/webapp/catalog/?lang=ru")
        self.assertEqual(response.data["products"][0]["name"], "Крем")

    def test_catalog_carries_shop_name_and_only_the_set_links(self):
        from apps.bot_settings.models import GlobalSettings

        conf = GlobalSettings.get()
        conf.shop_name = "Real Beauty"
        conf.instagram_url = "https://instagram.com/realbeauty_uz"
        conf.youtube_url = ""  # blank → its row must not appear
        conf.telegram_url = "https://t.me/realbeauty"
        conf.save()

        data = self.client.get("/api/v1/webapp/catalog/").data
        self.assertEqual(data["shop"]["name"], "Real Beauty")
        kinds = {link["kind"] for link in data["links"]}
        self.assertEqual(kinds, {"instagram", "telegram"})  # youtube omitted

    def test_catalog_ships_the_youtube_channel_by_default(self):
        """A fresh settings row already carries the shop's YouTube channel.

        The column shipped blank for a long time, and a blank URL is dropped
        from `links` — which is why the Mini App never showed a YouTube row
        even though the icon and styling were there waiting for it.
        """
        from apps.bot_settings.models import GlobalSettings

        links = {l["kind"]: l["url"] for l in self.client.get(
            "/api/v1/webapp/catalog/").data["links"]}
        self.assertEqual(
            links["youtube"], "https://www.youtube.com/@Realbeauty_uz1/shorts"
        )
        self.assertEqual(GlobalSettings.get().youtube_url, links["youtube"])
