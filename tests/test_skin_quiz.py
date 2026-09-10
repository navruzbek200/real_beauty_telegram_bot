from __future__ import annotations

from django.test import SimpleTestCase, TestCase

from apps.analytics.models import SkinQuizResult
from apps.analytics.skin_logic import (
    QUESTION_COUNT,
    QUESTION_IDS,
    THRESHOLD,
    analyze,
)
from apps.users.models import TelegramUser
from bot.handlers.quiz import render_question
from bot.i18n import LANGUAGES, t


def answers(**overrides: int) -> dict[str, int]:
    """A full sheet of zeros with the given questions overridden."""
    return {qid: 0 for qid in QUESTION_IDS} | overrides


class SkinTypeTests(SimpleTestCase):
    """
    Question 1 alone decides the type.

    The earlier version averaged all the answers, which mixed "my pores are
    big" into "how oily is my skin" and produced a type that matched nobody.
    """

    def test_q1_maps_to_the_four_types(self):
        cases = {
            0: "dry",
            1: "dry",
            2: "combined",
            3: "normal",
            4: "oily",
            5: "oily",
        }
        for value, expected in cases.items():
            with self.subTest(q1=value):
                self.assertEqual(analyze(answers(q1=value)).skin_type, expected)

    def test_other_answers_do_not_move_the_type(self):
        # Every problem question maxed out, question 1 says balanced.
        loaded = {qid: 5 for qid in QUESTION_IDS} | {"q1": 3}
        self.assertEqual(analyze(loaded).skin_type, "normal")

    def test_missing_answers_are_treated_as_zero(self):
        result = analyze({"q1": 4})
        self.assertEqual(result.skin_type, "oily")
        self.assertEqual(result.answers["q7"], 0)

    def test_out_of_range_answers_are_clamped(self):
        self.assertEqual(analyze({"q1": 99}).skin_type, "oily")
        self.assertEqual(analyze({"q1": -3}).skin_type, "dry")


class RecommendationTests(SimpleTestCase):
    def test_base_block_always_comes_first(self):
        result = analyze(answers(q1=0))
        self.assertEqual(result.recommendation_keys[0], "rec.base.dry")

    def test_only_answers_at_or_above_the_threshold_add_a_block(self):
        below = analyze(answers(q1=3, q2=THRESHOLD - 1))
        self.assertNotIn("rec.P0", below.recommendation_keys)

        at = analyze(answers(q1=3, q2=THRESHOLD))
        self.assertIn("rec.P0", at.recommendation_keys)

    def test_each_problem_question_maps_to_its_own_block(self):
        expected = {
            "q2": "rec.P0",
            "q3": "rec.S",
            "q5": "rec.Bh",
            "q6": "rec.Wh",
            "q7": "rec.P",
            "q8": "rec.Ew",
            "q9": "rec.Ed",
            "q10": "rec.W",
        }
        for qid, key in expected.items():
            with self.subTest(question=qid):
                result = analyze(answers(q1=3, **{qid: 5}))
                self.assertIn(key, result.recommendation_keys)

    def test_acne_advice_depends_on_how_oily_the_skin_is(self):
        # Drying treatments help oily skin and wreck a dry barrier, so the
        # same answer has to produce different advice.
        oily = analyze(answers(q1=5, q4=5))
        self.assertIn("rec.Ao", oily.recommendation_keys)
        self.assertNotIn("rec.Ad", oily.recommendation_keys)

        dry = analyze(answers(q1=0, q4=5))
        self.assertIn("rec.Ad", dry.recommendation_keys)
        self.assertNotIn("rec.Ao", dry.recommendation_keys)

    def test_a_clear_sheet_gets_only_the_base_advice(self):
        self.assertEqual(len(analyze(answers(q1=3)).recommendation_keys), 1)

    def test_every_recommendation_key_has_text_in_every_language(self):
        loaded = {qid: 5 for qid in QUESTION_IDS}
        for q1 in (0, 5):
            for key in analyze(loaded | {"q1": q1}).recommendation_keys:
                for code in LANGUAGES:
                    with self.subTest(key=key, language=code):
                        self.assertNotEqual(t(key, code), key)


class QuestionRenderingTests(SimpleTestCase):
    def test_there_are_ten_questions(self):
        self.assertEqual(QUESTION_COUNT, 10)

    def test_first_question_carries_labelled_options(self):
        _text, keyboard = render_question(0, "uz")
        labels = [b.text for row in keyboard.inline_keyboard for b in row]
        self.assertEqual(len(labels), 6)  # no back button on the first question
        self.assertIn("0 · Juda quruq tortiladi", labels)

    def test_later_questions_use_the_digit_scale_and_a_back_button(self):
        text, keyboard = render_question(4, "uz")
        labels = [b.text for row in keyboard.inline_keyboard for b in row]
        self.assertEqual(len(labels), 7)  # six digits + back
        self.assertIn("⬅️ Orqaga", labels)
        self.assertIn("Savol 5/10", text)

    def test_renders_in_every_language(self):
        for code in LANGUAGES:
            for index in range(QUESTION_COUNT):
                with self.subTest(language=code, index=index):
                    text, keyboard = render_question(index, code)
                    self.assertTrue(text.strip())
                    self.assertTrue(keyboard.inline_keyboard)


class QuizPersistenceTests(TestCase):
    def setUp(self):
        self.user = TelegramUser.objects.create(
            telegram_id=5001,
            full_name="Test Mijoz",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )

    def _save(self, sheet):
        from asgiref.sync import async_to_sync

        from bot.services import quiz_service

        return async_to_sync(quiz_service.save_result)(
            telegram_id=self.user.telegram_id, result=analyze(sheet), language="uz"
        )

    def test_result_is_stored_and_adopted_as_the_skin_type(self):
        row = self._save(answers(q1=5, q2=4))

        self.assertIsNotNone(row)
        self.user.refresh_from_db()
        self.assertEqual(self.user.face_condition, "oily")

        stored = SkinQuizResult.objects.get(pk=row.pk)
        self.assertEqual(stored.answers["q2"], 4)
        self.assertIn("rec.P0", stored.recommendation_keys)

    def test_retaking_the_quiz_replaces_the_verdict_and_keeps_both_runs(self):
        self._save(answers(q1=5))
        self._save(answers(q1=0))

        self.user.refresh_from_db()
        self.assertEqual(self.user.face_condition, "dry")
        # Every run is kept: the shop reads how a customer's skin changed.
        self.assertEqual(SkinQuizResult.objects.filter(user=self.user).count(), 2)

    def test_unknown_customer_is_not_an_error(self):
        from asgiref.sync import async_to_sync

        from bot.services import quiz_service

        row = async_to_sync(quiz_service.save_result)(
            telegram_id=999999, result=analyze(answers(q1=1)), language="uz"
        )
        self.assertIsNone(row)
