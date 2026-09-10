from __future__ import annotations

from django.test import SimpleTestCase

from bot import i18n
from bot.filters.menu import MenuText
from bot.i18n import en, ru, uz
from bot.keyboards import reply
from core.i18n import pick


class CatalogueParityTests(SimpleTestCase):
    """
    Every key must exist in all three languages.

    A key present only in Uzbek falls back silently, so a missing Russian
    string ships as a Russian screen with one Uzbek line on it — the kind of
    thing nobody notices until a customer does.
    """

    def test_all_languages_define_the_same_keys(self):
        base = set(uz.STRINGS)
        for code, module in (("ru", ru), ("en", en)):
            with self.subTest(language=code):
                self.assertEqual(set(module.STRINGS), base)

    def test_no_empty_strings(self):
        for code in i18n.LANGUAGES:
            for key in uz.STRINGS:
                with self.subTest(language=code, key=key):
                    self.assertTrue(i18n.t(key, code).strip())

    def test_placeholders_match_across_languages(self):
        import re

        pattern = re.compile(r"{(\w+)}")
        for key, template in uz.STRINGS.items():
            expected = set(pattern.findall(template))
            for code, module in (("ru", ru), ("en", en)):
                with self.subTest(key=key, language=code):
                    self.assertEqual(
                        set(pattern.findall(module.STRINGS[key])), expected
                    )


class TranslateTests(SimpleTestCase):
    def test_returns_requested_language(self):
        self.assertEqual(i18n.t("menu.catalog", "ru"), ru.STRINGS["menu.catalog"])
        self.assertEqual(i18n.t("menu.catalog", "en"), en.STRINGS["menu.catalog"])

    def test_unknown_language_falls_back_to_uzbek(self):
        self.assertEqual(i18n.t("menu.catalog", "fr"), uz.STRINGS["menu.catalog"])

    def test_missing_key_returns_the_key_rather_than_raising(self):
        self.assertEqual(i18n.t("nope.not.here", "uz"), "nope.not.here")

    def test_bad_placeholder_degrades_to_the_raw_template(self):
        # A caller that forgets an argument gets slightly odd text, not a crash
        # that takes the whole handler down.
        self.assertIn("{name}", i18n.t("user.welcome_back", "uz"))

    def test_normalize_maps_regional_tags(self):
        self.assertEqual(i18n.normalize("ru-RU"), "ru")
        self.assertEqual(i18n.normalize("en_GB"), "en")
        self.assertEqual(i18n.normalize("kk"), "ru")  # CIS locales read Russian
        self.assertEqual(i18n.normalize(None), "uz")
        self.assertEqual(i18n.normalize(""), "uz")


class MenuMatchingTests(SimpleTestCase):
    def test_variants_covers_every_language(self):
        labels = i18n.variants("menu.catalog")
        self.assertEqual(len(labels), 3)
        self.assertIn(uz.STRINGS["menu.catalog"], labels)
        self.assertIn(ru.STRINGS["menu.catalog"], labels)

    async def _matches(self, filt, text):
        class FakeMessage:
            def __init__(self, text):
                self.text = text

        return await filt(FakeMessage(text))

    async def test_filter_matches_any_language(self):
        filt = MenuText("menu.top")
        for code in i18n.LANGUAGES:
            self.assertTrue(await self._matches(filt, i18n.t("menu.top", code)))
        self.assertFalse(await self._matches(filt, "something else"))

    async def test_filter_still_matches_the_old_label(self):
        # Customers keep an old keyboard on screen for months; the renamed
        # "Qo'llanmalar" button has to keep working after the rename.
        filt = MenuText("menu.ingredients", "menu.legacy_tutorials")
        self.assertTrue(await self._matches(filt, "📚 Qo'llanmalar"))
        self.assertTrue(
            await self._matches(filt, uz.STRINGS["menu.ingredients"])
        )


class MainMenuKeyboardTests(SimpleTestCase):
    def test_renders_in_each_language(self):
        # Six buttons in three even rows: catalogue, discounts, bonuses,
        # profile, face analysis, support. Lessons live in the Mini App's
        # «Darslar» tab, top products in its TOP filter, retaking the quiz in
        # Profil — none of those needs a top-level button (their old labels
        # still route via MenuText).
        expected = [
            "menu.catalog", "menu.discounts", "menu.bonus",
            "menu.profile", "menu.face_analysis", "menu.support",
        ]
        for code in i18n.LANGUAGES:
            with self.subTest(language=code):
                labels = [
                    button.text
                    for row in reply.main_menu_keyboard(code).keyboard
                    for button in row
                ]
                self.assertEqual(len(labels), 6)
                for key in expected:
                    self.assertIn(i18n.t(key, code), labels)
                self.assertNotIn(i18n.t("menu.top", code), labels)
                self.assertNotIn(i18n.t("menu.ingredients", code), labels)

    def test_old_lesson_labels_still_route_to_a_handler(self):
        # The button left the keyboard, but keyboards already on customers'
        # screens keep the old label forever — MenuText must still match it.
        from bot.filters.menu import MenuText

        menu_filter = MenuText("menu.ingredients", "menu.legacy_tutorials")
        for label in (i18n.t("menu.ingredients", "uz"), "📚 Qo'llanmalar"):
            self.assertIn(label, menu_filter.labels)


class PickTests(SimpleTestCase):
    class Thing:
        name = "Asosiy"
        name_ru = "Основной"
        name_en = ""

    def test_uses_translation_when_present(self):
        self.assertEqual(pick(self.Thing(), "name", "ru"), "Основной")

    def test_falls_back_to_uzbek_when_translation_is_blank(self):
        self.assertEqual(pick(self.Thing(), "name", "en"), "Asosiy")

    def test_falls_back_when_the_field_does_not_exist(self):
        self.assertEqual(pick(self.Thing(), "name", "de"), "Asosiy")
