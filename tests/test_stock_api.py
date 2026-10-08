"""
Taking a product off sale from the panel.

Stock is a second, softer switch next to `is_active`, and the difference is
the whole point: clearing `is_active` removes a product from the shop window,
while clearing `in_stock` leaves it there, marked, saying it will be back. A
shop that only had the hard switch lost the place a product held in the
customer's mind every time it ran out.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from apps.products.models import Product


class StockToggleApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = get_user_model().objects.create_superuser(
            "owner", "o@example.com", "pw"
        )
        self.client.force_authenticate(self.owner)
        self.product = Product.objects.create(name="Serum", current_price=100_000)

    def test_a_product_is_on_sale_when_it_is_created(self):
        self.assertTrue(self.product.in_stock)

    def test_marking_it_out_of_stock_keeps_it_in_the_catalogue(self):
        response = self.client.post(
            "/api/v1/products/mark_out_of_stock/", {"ids": [self.product.pk]}, format="json"
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["updated"], 1)
        self.product.refresh_from_db()
        self.assertFalse(self.product.in_stock)
        # The hard switch is untouched — this is a pause, not a removal.
        self.assertTrue(self.product.is_active)

    def test_putting_it_back_on_sale(self):
        Product.objects.filter(pk=self.product.pk).update(in_stock=False)

        self.client.post(
            "/api/v1/products/mark_in_stock/", {"ids": [self.product.pk]}, format="json"
        )

        self.product.refresh_from_db()
        self.assertTrue(self.product.in_stock)

    def test_several_at_once(self):
        second = Product.objects.create(name="Krem", current_price=90_000)

        response = self.client.post(
            "/api/v1/products/mark_out_of_stock/",
            {"ids": [self.product.pk, second.pk]},
            format="json",
        )

        self.assertEqual(response.data["updated"], 2)
        self.assertFalse(Product.objects.get(pk=second.pk).in_stock)

    def test_the_list_can_be_filtered_by_stock(self):
        sold_out = Product.objects.create(name="Krem", current_price=90_000, in_stock=False)

        on_sale = self.client.get("/api/v1/products/?in_stock=true").data["results"]
        gone = self.client.get("/api/v1/products/?in_stock=false").data["results"]

        self.assertEqual([p["id"] for p in on_sale], [self.product.pk])
        self.assertEqual([p["id"] for p in gone], [sold_out.pk])

    def test_a_signed_out_visitor_changes_nothing(self):
        self.client.force_authenticate(None)

        response = self.client.post(
            "/api/v1/products/mark_out_of_stock/", {"ids": [self.product.pk]}, format="json"
        )

        self.assertIn(response.status_code, (401, 403))
        self.product.refresh_from_db()
        self.assertTrue(self.product.in_stock)


class StockInTheMiniAppTests(APITestCase):
    """What the shopfront does with a product that is out of stock."""

    def setUp(self):
        self.client = APIClient()
        self.product = Product.objects.create(name="Serum", current_price=100_000)

    def test_it_stays_in_the_catalogue_flagged(self):
        Product.objects.filter(pk=self.product.pk).update(in_stock=False)

        items = self.client.get("/api/v1/webapp/catalog/?lang=uz").data["products"]

        self.assertEqual(len(items), 1)
        self.assertFalse(items[0]["in_stock"])

    def test_deactivating_it_removes_it_entirely(self):
        Product.objects.filter(pk=self.product.pk).update(is_active=False)

        items = self.client.get("/api/v1/webapp/catalog/?lang=uz").data["products"]

        self.assertEqual(items, [])


class ProductListOrderingTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(
            get_user_model().objects.create_superuser("owner", "o@example.com", "pw")
        )

    def test_paging_the_catalogue_is_deterministic(self):
        # Without a default ordering Postgres may return rows in any order,
        # and the panel then shows one product twice while dropping another.
        for i in range(7):
            Product.objects.create(name=f"Mahsulot {i}", current_price=1000)

        first = self.client.get("/api/v1/products/?page_size=3").data["results"]
        again = self.client.get("/api/v1/products/?page_size=3").data["results"]
        second = self.client.get("/api/v1/products/?page_size=3&page=2").data["results"]

        self.assertEqual([p["id"] for p in first], [p["id"] for p in again])
        self.assertFalse(
            set(p["id"] for p in first) & set(p["id"] for p in second),
            "a product appeared on two pages",
        )
