"""
Phone numbers are the key the bot links a customer to their CRM card by, so
what counts as "the same number" has to survive every way a person types it —
and the shop serves customers abroad, not only in Uzbekistan.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from apps.users.models import TelegramUser

normalize = TelegramUser.normalize_phone
tail = TelegramUser.phone_tail_of


class UzbekDefaultTests(SimpleTestCase):
    def test_a_bare_local_number_defaults_to_uzbekistan(self):
        self.assertEqual(normalize("90 123 45 67"), "+998901234567")

    def test_various_uzbek_spellings_land_on_one_form(self):
        for raw in (
            "+998 90 123 45 67",
            "998901234567",
            "+998901234567",
            "(90) 123-45-67",
        ):
            with self.subTest(raw=raw):
                self.assertEqual(normalize(raw), "+998901234567")


class ForeignNumberTests(SimpleTestCase):
    def test_russia_is_detected_from_the_country_code(self):
        self.assertEqual(normalize("+7 916 123 45 67"), "+79161234567")

    def test_a_russian_contact_without_a_plus_still_works(self):
        # Telegram hands a shared contact over without the leading "+".
        self.assertEqual(normalize("79161234567"), "+79161234567")

    def test_us_number_is_detected(self):
        self.assertEqual(normalize("+1 202 555 0123"), "+12025550123")


class RejectionTests(SimpleTestCase):
    def test_junk_and_empty_are_rejected(self):
        for raw in ("", None, "   ", "abc", "123", "90 123"):
            with self.subTest(raw=raw):
                self.assertIsNone(normalize(raw))


class MatchingKeyTests(SimpleTestCase):
    """The bot matches CRM and Telegram rows on the last 9 digits."""

    def test_the_same_person_matches_across_formats(self):
        self.assertEqual(tail(normalize("90 123 45 67")), tail("998901234567"))

    def test_a_foreign_number_matches_on_its_own_tail(self):
        self.assertEqual(tail(normalize("+7 916 123 45 67")), tail("79161234567"))
