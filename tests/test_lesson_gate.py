"""
The gate on the video course.

What matters here is not only that a wrong word is refused, but that a locked
answer carries nothing — a customer who never bought anything must not be able
to read the course's contents out of the API response, which is where a gate
that only hides the UI would leak.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import urlencode

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.lessons.models import AccessCode, LessonUnlock, LessonVideo, normalize_code
from apps.lessons.services import published_videos, redeem
from apps.users.models import TelegramUser

BOT_TOKEN = "123456:TEST-token-for-the-suite"


def init_data_for(telegram_id: int, token: str = BOT_TOKEN) -> str:
    """A Mini App initData string signed the way Telegram signs one."""
    pairs = {
        "auth_date": "1700000000",
        "query_id": "AAA",
        "user": json.dumps({"id": telegram_id, "first_name": "Sinov"}),
    }
    check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    pairs["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(pairs)


@override_settings(BOT_TOKEN=BOT_TOKEN)
class LessonGateApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = TelegramUser.objects.create(
            telegram_id=9001,
            full_name="Sinov Mijoz",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )
        self.video = LessonVideo.objects.create(
            title="Terini tozalash",
            description="Kechqurungi tartib",
            order=1,
            video_file_id="cached-id-1",
        )
        self.code = AccessCode.objects.create(code="NURLI2026", label="Asosiy")
        self.lessons_url = reverse("api_webapp_lessons")
        self.unlock_url = reverse("api_webapp_unlock")

    def test_a_locked_answer_carries_no_titles(self):
        res = self.client.get(self.lessons_url, {"lang": "uz"})

        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertTrue(body["locked"])
        self.assertEqual(body["videos"], [])
        # Not even the number of lessons: a locked answer says nothing about
        # the course beyond the fact that there is one.
        self.assertNotIn("available", body)
        self.assertNotIn("Terini tozalash", res.content.decode())

    def test_a_correct_word_opens_the_course(self):
        res = self.client.post(
            self.unlock_url,
            {"init_data": init_data_for(9001), "code": "NURLI2026"},
            content_type="application/json",
        )

        self.assertTrue(res.json()["ok"])
        self.assertTrue(LessonUnlock.objects.filter(user=self.user).exists())
        self.code.refresh_from_db()
        self.assertEqual(self.code.uses_count, 1)

        after = self.client.get(
            self.lessons_url, {"lang": "uz", "init_data": init_data_for(9001)}
        ).json()
        self.assertFalse(after["locked"])
        self.assertEqual(after["videos"][0]["title"], "Terini tozalash")

    def test_a_word_typed_loosely_still_works(self):
        # Read off a receipt, retyped on a phone: case and dashes carry no
        # meaning and must not be the reason a paying customer is refused.
        res = self.client.post(
            self.unlock_url,
            {"init_data": init_data_for(9001), "code": " nurli-2026 "},
            content_type="application/json",
        )

        self.assertTrue(res.json()["ok"])

    def test_a_wrong_word_is_refused_and_opens_nothing(self):
        res = self.client.post(
            self.unlock_url,
            {"init_data": init_data_for(9001), "code": "QALAY"},
            content_type="application/json",
        )

        body = res.json()
        self.assertFalse(body["ok"])
        self.assertEqual(body["reason"], "unknown_code")
        self.assertFalse(LessonUnlock.objects.filter(user=self.user).exists())
        self.code.refresh_from_db()
        self.assertEqual(self.code.uses_count, 0)

    def test_a_forged_signature_is_refused(self):
        forged = init_data_for(9001, token="999:someone-elses-bot")

        res = self.client.post(
            self.unlock_url,
            {"init_data": forged, "code": "NURLI2026"},
            content_type="application/json",
        )

        self.assertEqual(res.status_code, 403)
        self.assertFalse(LessonUnlock.objects.filter(user=self.user).exists())

    def test_a_one_seat_word_is_spent_after_its_customer(self):
        one_seat = AccessCode.objects.create(code="BIRTA", max_uses=1)
        other = TelegramUser.objects.create(
            telegram_id=9002,
            full_name="Ikkinchi",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )

        self.assertTrue(redeem(self.user, "BIRTA").ok)
        second = redeem(other, "BIRTA")

        self.assertFalse(second.ok)
        self.assertEqual(second.reason, "code_spent")

    def test_an_expired_word_is_refused(self):
        AccessCode.objects.create(
            code="ESKI", expires_at=timezone.now() - timedelta(minutes=1)
        )

        result = redeem(self.user, "ESKI")

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "code_expired")

    def test_a_switched_off_word_is_refused(self):
        AccessCode.objects.create(code="OCHIQ", is_active=False)

        result = redeem(self.user, "OCHIQ")

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "code_inactive")

    def test_an_unlocked_customer_stays_unlocked_without_spending_a_seat(self):
        one_seat = AccessCode.objects.create(code="YAGONA", max_uses=1)
        self.assertTrue(redeem(self.user, "YAGONA").ok)

        # Re-entering after reinstalling Telegram must not burn the last seat,
        # and must not fail once the word itself is switched off. Reload first:
        # the counter was bumped with an UPDATE, so this instance is stale and
        # saving it as-is would write the old value back.
        one_seat.refresh_from_db()
        one_seat.is_active = False
        one_seat.save()
        again = redeem(self.user, "YAGONA")

        self.assertTrue(again.ok)
        one_seat.refresh_from_db()
        self.assertEqual(one_seat.uses_count, 1)
        self.assertEqual(LessonUnlock.objects.filter(user=self.user).count(), 1)

    def test_guessing_is_rate_limited(self):
        init = init_data_for(9001)
        for _ in range(8):
            self.client.post(
                self.unlock_url,
                {"init_data": init, "code": "XATO"},
                content_type="application/json",
            )

        blocked = self.client.post(
            self.unlock_url,
            {"init_data": init, "code": "XATO"},
            content_type="application/json",
        )

        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.json()["reason"], "too_many")

    def test_a_lesson_without_a_video_is_not_published(self):
        LessonVideo.objects.create(title="Hali tayyor emas", order=2)

        titles = [v.title for v in published_videos()]

        self.assertEqual(titles, ["Terini tozalash"])

    def test_a_hidden_lesson_is_not_published(self):
        self.video.is_active = False
        self.video.save()

        self.assertEqual(published_videos(), [])


class CodeNormalizationTests(TestCase):
    def test_punctuation_and_case_are_ignored(self):
        self.assertEqual(normalize_code(" nurli-2026 "), "NURLI2026")
        self.assertEqual(normalize_code("NURLI 2026"), "NURLI2026")
        self.assertEqual(normalize_code(""), "")

    def test_a_saved_code_is_stored_in_its_canonical_form(self):
        row = AccessCode.objects.create(code="  yoz-aksiya  ")

        self.assertEqual(row.code, "YOZAKSIYA")


@override_settings(BOT_TOKEN=BOT_TOKEN)
class LessonDeepLinkGateTests(TestCase):
    """The bot re-checks the gate.

    A `vlesson_<id>` deep link is a plain t.me URL. Anyone who has seen one can
    retype it with a different id, or send it to a friend who never paid — so
    the bot cannot treat "the Mini App sent them here" as proof of anything.
    """

    def setUp(self):
        from tests.test_webapp_lessons import BOT_ID  # noqa: F401  (shared fixture)

        self.user = TelegramUser.objects.create(
            telegram_id=7001,
            full_name="Mijoz",
            language="uz",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )
        self.video = LessonVideo.objects.create(
            title="Terini tozalash", order=1, video_file_id="cached-id-1"
        )

    def _run(self, payload: str):
        from asgiref.sync import async_to_sync

        from bot.handlers import auth
        from tests.test_webapp_lessons import FakeMessage, fsm_for

        msg = FakeMessage(7001)
        handled = async_to_sync(auth._handled_as_action)(msg, fsm_for(7001), None, payload)
        return handled, msg

    def test_a_locked_customer_is_told_instead_of_shown(self):
        from unittest.mock import AsyncMock, patch

        with patch("bot.utils.video.send_lesson_video", new=AsyncMock()) as sender:
            handled, msg = self._run(f"vlesson_{self.video.pk}")

        self.assertTrue(handled)
        sender.assert_not_awaited()
        self.assertIn("yopiq", msg.sent[0]["text"].lower())

    def test_an_unlocked_customer_gets_the_video(self):
        from unittest.mock import AsyncMock, patch

        LessonUnlock.objects.create(user=self.user)

        with patch("bot.utils.video.send_lesson_video", new=AsyncMock()) as sender:
            handled, msg = self._run(f"vlesson_{self.video.pk}")

        self.assertTrue(handled)
        sender.assert_awaited_once()

    def test_an_unknown_lesson_id_says_so(self):
        from unittest.mock import AsyncMock, patch

        LessonUnlock.objects.create(user=self.user)

        with patch("bot.utils.video.send_lesson_video", new=AsyncMock()) as sender:
            handled, msg = self._run("vlesson_999999")

        self.assertTrue(handled)
        sender.assert_not_awaited()
        self.assertEqual(len(msg.sent), 1)


class IssueCodesAdminTests(TestCase):
    """The counter's one-tap button for minting a code per buyer."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        User.objects.create_superuser("boss", "boss@example.com", "pw")
        self.client.login(username="boss", password="pw")
        self.url = reverse("admin:lessons_accesscode_issue")

    def test_issuing_mints_single_use_codes_and_shows_them_once(self):
        res = self.client.post(self.url, {"count": 5}, follow=True)

        made = AccessCode.objects.all()
        self.assertEqual(made.count(), 5)
        self.assertTrue(all(c.max_uses == 1 for c in made))
        self.assertEqual(len({c.code for c in made}), 5)

        shown = res.context["fresh_codes"]
        self.assertEqual(sorted(shown), sorted(c.code for c in made))

        # Shown once: a reload must not re-print codes that were already read
        # out at the counter.
        again = self.client.get(reverse("admin:lessons_accesscode_changelist"))
        self.assertIsNone(again.context["fresh_codes"])

    def test_an_unlisted_count_falls_back_to_one(self):
        self.client.post(self.url, {"count": "9999"})

        self.assertEqual(AccessCode.objects.count(), 1)

    def test_a_get_mints_nothing(self):
        self.client.get(self.url)

        self.assertEqual(AccessCode.objects.count(), 0)

    def test_a_signed_out_visitor_mints_nothing(self):
        self.client.logout()

        self.client.post(self.url, {"count": 5})

        self.assertEqual(AccessCode.objects.count(), 0)


class SpentCodeCleanupTests(TestCase):
    """Tidying the codes list must not take anyone's course away."""

    def setUp(self):
        self.user = TelegramUser.objects.create(
            telegram_id=8100,
            full_name="Mijoz",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )
        self.code = AccessCode.objects.create(code="BIRMARTA", max_uses=1)

    def test_deleting_a_spent_code_leaves_its_customer_unlocked(self):
        self.assertTrue(redeem(self.user, "BIRMARTA").ok)

        self.code.delete()

        # The unlock row survives with a null pointer, so the customer keeps
        # what they paid for even after the shop clears old codes away.
        unlock = LessonUnlock.objects.get(user=self.user)
        self.assertIsNone(unlock.code)
        from apps.lessons.services import is_unlocked

        self.assertTrue(is_unlocked(self.user))

    def test_access_granted_by_hand_needs_no_code(self):
        from apps.lessons.services import is_unlocked

        # What the shop does when a customer deletes Telegram and comes back
        # as a new account, or simply loses the word they were given.
        LessonUnlock.objects.create(user=self.user)

        self.assertTrue(is_unlocked(self.user))

    def test_a_fresh_telegram_account_starts_locked(self):
        from apps.lessons.services import is_unlocked

        self.assertTrue(redeem(self.user, "BIRMARTA").ok)
        reinstalled = TelegramUser.objects.create(
            telegram_id=8101,
            full_name="Mijoz (yangi akkaunt)",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )

        # Deleting Telegram and signing up again produces a different id, so
        # the shop has to re-open the course deliberately — the spent code
        # will not do it a second time.
        self.assertFalse(is_unlocked(reinstalled))
        self.assertEqual(redeem(reinstalled, "BIRMARTA").reason, "code_spent")


@override_settings(BOT_TOKEN=BOT_TOKEN, WEBAPP_URL="https://example.test/webapp/")
class UnlockFromReplyKeyboardTests(TestCase):
    """Redeeming a word when the Mini App has no signature to offer.

    Telegram signs initData only for launches the bot is expected to verify
    out of band. Opened from the reply-keyboard button — which is how the main
    menu reaches the app — there is no signature at all, so the HTTP endpoint
    can never work from there. The payload comes back through Telegram
    instead, as a message from an account Telegram has already authenticated.
    """

    def setUp(self):
        from asgiref.sync import async_to_sync  # noqa: F401

        self.user = TelegramUser.objects.create(
            telegram_id=7200,
            full_name="Mijoz",
            language="uz",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )
        self.video = LessonVideo.objects.create(
            title="Terini tozalash", order=1, video_file_id="cached-id-1"
        )
        self.code = AccessCode.objects.create(code="BIRMARTA", max_uses=1)

    def _send(self, payload: dict):
        import json as _json

        from asgiref.sync import async_to_sync

        from bot.handlers import support
        from tests.test_webapp_lessons import FakeMessage, fsm_for

        msg = FakeMessage(7200)
        msg.web_app_data = SimpleNamespace(data=_json.dumps(payload))
        msg.bot = None
        async_to_sync(support.from_webapp)(msg, fsm_for(7200), "uz")
        return msg

    def test_a_correct_word_opens_the_course_and_offers_the_way_back(self):
        msg = self._send({"action": "unlock", "code": "birmarta"})

        self.assertTrue(LessonUnlock.objects.filter(user=self.user).exists())
        self.assertIn("ochildi", msg.sent[0]["text"].lower())
        # sendData closes the app, so the reply has to carry the way back in.
        self.assertIsNotNone(msg.sent[0]["reply_markup"])

    def test_a_spent_word_says_which_thing_went_wrong(self):
        other = TelegramUser.objects.create(
            telegram_id=7201,
            full_name="Boshqa",
            registration_status=TelegramUser.RegistrationStatus.COMPLETED,
        )
        redeem(other, "BIRMARTA")

        msg = self._send({"action": "unlock", "code": "BIRMARTA"})

        self.assertFalse(LessonUnlock.objects.filter(user=self.user).exists())
        self.assertIn("ishlatilgan", msg.sent[0]["text"].lower())

    def test_a_locked_customer_asking_for_a_lesson_is_refused(self):
        from unittest.mock import AsyncMock, patch

        with patch("bot.utils.video.send_lesson_video", new=AsyncMock()) as sender:
            msg = self._send({"action": "vlesson", "id": self.video.pk})

        sender.assert_not_awaited()
        self.assertIn("yopiq", msg.sent[0]["text"].lower())

    def test_an_unlocked_customer_gets_the_lesson(self):
        from unittest.mock import AsyncMock, patch

        LessonUnlock.objects.create(user=self.user)

        with patch("bot.utils.video.send_lesson_video", new=AsyncMock()) as sender:
            self._send({"action": "vlesson", "id": self.video.pk})

        sender.assert_awaited_once()

    def test_a_lesson_request_does_not_fall_into_the_support_flow(self):
        # The bug this covers: an unknown action lands in "write us a
        # question", so before vlesson was handled a customer tapping a lesson
        # was silently asked to type a support message instead.
        from unittest.mock import AsyncMock, patch

        LessonUnlock.objects.create(user=self.user)

        with patch("bot.utils.video.send_lesson_video", new=AsyncMock()):
            msg = self._send({"action": "vlesson", "id": self.video.pk})

        self.assertEqual(msg.sent, [])
