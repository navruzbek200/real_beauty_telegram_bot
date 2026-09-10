from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.bot_settings.models import Discount, GlobalSettings
from apps.campaigns.models import AutoMessage, MessageTemplate
from apps.loyalty.models import LoyaltySettings, Reward
from apps.products.models import Product, ProductTutorialStep
from apps.users.models import SellerProfile, TelegramUser, UserProduct

User = get_user_model()

TEMPLATES: list[dict[str, str]] = [
    {
        "name": "welcome_uz",
        "template_type": MessageTemplate.TemplateType.WELCOME,
        "body": (
            "🎉 <b>{{ user.full_name }}</b>, Real Beauty oilasiga xush kelibsiz!\n\n"
            "Xaridingiz uchun rahmat. Quyida mahsulotdan foydalanish "
            "bo'yicha qo'llanmalarni topasiz. Pastdagi menyudan foydalaning 👇"
        ),
    },
    {
        "name": "product_intro_uz",
        "template_type": MessageTemplate.TemplateType.PRODUCT_INTRO,
        "body": (
            "📘 <b>{{ product.name }}</b> uchun qo'llanma.\n\n"
            "Har bir bosqichni ko'rish uchun quyidagi tugmalarni bosing:"
        ),
    },
    {
        "name": "week1_uz",
        "template_type": MessageTemplate.TemplateType.WEEK1_CHECKIN,
        "body": (
            "👋 Salom, {{ user.full_name }}!\n\n"
            "<b>{{ product.name }}</b> mahsulotidan foydalanayotganingizga bir hafta "
            "bo'ldi. O'zingizni qanday his qilyapsiz? Fikringizni bildiring 👇"
        ),
    },
    {
        "name": "week2_uz",
        "template_type": MessageTemplate.TemplateType.WEEK2_PROGRESS,
        "body": (
            "✨ {{ user.full_name }}, <b>{{ product.name }}</b> bilan 2 hafta!\n\n"
            "Teringizda o'zgarish sezdingizmi? Oldin va keyin rasmlaringizni "
            "yuborishingiz mumkin 👇"
        ),
    },
    {
        "name": "birthday_uz",
        "template_type": MessageTemplate.TemplateType.BIRTHDAY_SALE,
        "body": (
            "🎂 <b>{{ user.full_name }}</b>, tug'ilgan kuningiz muborak!\n\n"
            "Sizga sovg'a — barcha mahsulotlarga <b>{{ discount }}%</b> chegirma! 🎁"
        ),
    },
    {
        "name": "feedback_thanks_uz",
        "template_type": MessageTemplate.TemplateType.FEEDBACK_THANKS,
        "body": "🙏 Fikringiz uchun katta rahmat! Biz uchun juda muhim.",
    },
]

PRODUCTS: list[dict[str, Any]] = [
    {
        "name": "Real Beauty Vitamin C Serum",
        "name_ru": "Real Beauty сыворотка с витамином C",
        "name_en": "Real Beauty Vitamin C Serum",
        "description": "Yorqin va tekis teri uchun C vitaminli zardob.",
        "description_ru": "Сыворотка с витамином C для сияющей ровной кожи.",
        "description_en": "A vitamin C serum for bright, even skin.",
        "is_top": True,
        "top_order": 1,
        "top_note": "Eng ko'p sotilgan",
        "steps": [
            ("1-bosqich: Yuzni tozalash", "Avval yuzingizni yuving va quriting."),
            ("2-bosqich: Zardobni surtish", "2-3 tomchi zardobni yuzga surting."),
            ("3-bosqich: Namlash", "Yengil harakatlar bilan singdiring."),
        ],
    },
    {
        "name": "Real Beauty Night Cream",
        "name_ru": "Real Beauty ночной крем",
        "name_en": "Real Beauty Night Cream",
        "description": "Tunda terini tiklovchi krem.",
        "description_ru": "Ночной крем, восстанавливающий кожу.",
        "description_en": "A night cream that repairs skin while you sleep.",
        "is_top": True,
        "top_order": 2,
        "top_note": "Yangi kelgan",
        "steps": [
            ("1-bosqich: Tayyorgarlik", "Uxlashdan oldin yuzni tozalang."),
            ("2-bosqich: Kremni surtish", "Bir oz kremni yuzga teng surting."),
        ],
    },
]

DISCOUNTS: list[dict[str, Any]] = [
    {
        "title": "Yozgi aksiya",
        "percent": 20,
        "description": "Barcha zardoblarga 20% chegirma.",
        "promo_code": "SUMMER20",
    },
    {
        "title": "Yangi mijozlar uchun",
        "percent": 15,
        "description": "Birinchi xaridga 15% chegirma.",
        "promo_code": "WELCOME15",
    },
]


class Command(BaseCommand):
    help = "Seed demo data (templates, products, discounts, seller, sample user)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--seller-telegram-id",
            type=int,
            default=111111111,
            help="Telegram ID for the demo seller's referral link.",
        )
        parser.add_argument(
            "--user-telegram-id",
            type=int,
            default=222222222,
            help="Telegram ID for the sample completed bot user.",
        )

    def handle(self, *args: Any, **opts: Any) -> None:
        self._settings()
        self._templates()
        self._auto_messages()
        products = self._products()
        self._discounts()
        self._loyalty()
        seller = self._seller(opts["seller_telegram_id"])
        user = self._sample_user(opts["user_telegram_id"], products[0], seller)
        self._loyalty_demo(user, products)
        self.stdout.write(self.style.SUCCESS("✅ Demo ma'lumotlar tayyor."))

    # -- pieces --------------------------------------------------------------
    def _settings(self) -> None:
        GlobalSettings.get()
        self.stdout.write("• Umumiy sozlamalar OK")

    def _auto_messages(self) -> None:
        """
        One real rule and one ready-made test rule.

        The test rule ships switched off: it fires a minute after a purchase,
        which is exactly what you want when checking the pipeline and exactly
        what you do not want running unattended.
        """
        AutoMessage.objects.update_or_create(
            name="1-hafta — fikr so'rovi",
            defaults={
                "trigger": AutoMessage.Trigger.AFTER_PURCHASE,
                "delay_value": 7,
                "delay_unit": AutoMessage.Unit.DAY,
                "body": (
                    "👋 Salom, {{ user.full_name }}!\n\n"
                    "<b>{{ product.name }}</b> mahsulotidan foydalanayotganingizga "
                    "bir hafta bo'ldi. Yaxshi kelayaptimi?"
                ),
                "button_action": AutoMessage.Action.NONE,
                "button_label": "",
                "is_active": True,
            },
        )
        AutoMessage.objects.update_or_create(
            name="SINOV — 1 daqiqadan keyin keshbek taklifi",
            defaults={
                "trigger": AutoMessage.Trigger.AFTER_PURCHASE,
                "delay_value": 1,
                "delay_unit": AutoMessage.Unit.MINUTE,
                "body": (
                    "🎉 Tabriklaymiz, {{ user.full_name }}!\n\n"
                    "Siz <b>30% keshbek</b> yutib olish imkoniga egasiz. "
                    "Chegirmalarni ko'ring 👇"
                ),
                "button_action": AutoMessage.Action.DISCOUNTS,
                "button_label": "Chegirmalarni ko'rish",
                "is_active": False,
                "is_test_mode": True,
            },
        )
        self.stdout.write("• Avtomatik xabarlar OK (biri sinov uchun, o'chirilgan)")

    def _loyalty(self) -> None:
        LoyaltySettings.get()
        for title, cost, prefix in [
            ("500 so'mlik chegirma kuponi", 500, "RB500"),
            ("Bepul mini krem", 1200, "MINI"),
            ("Tekin konsultatsiya", 800, "CONS"),
        ]:
            Reward.objects.update_or_create(
                title=title,
                defaults={"cost_points": cost, "code_prefix": prefix, "is_active": True},
            )
        self.stdout.write("• Bonus dasturi + 3 ta sovg'a OK")

    def _templates(self) -> None:
        for t in TEMPLATES:
            # Keyed on template_type (unique): the 0004 migration already
            # seeded one row per type, and matching on name would try to
            # create a second row of the same type and hit the constraint.
            MessageTemplate.objects.update_or_create(
                template_type=t["template_type"],
                defaults={
                    "name": t["name"],
                    "body": t["body"],
                    "parse_mode": "HTML",
                    "is_active": True,
                },
            )
        self.stdout.write(f"• {len(TEMPLATES)} ta shablon OK")

    def _products(self) -> list[Product]:
        result: list[Product] = []
        for p in PRODUCTS:
            product, _ = Product.objects.update_or_create(
                name=p["name"],
                defaults={
                    key: value
                    for key, value in p.items()
                    if key not in {"name", "steps"}
                }
                | {"is_active": True},
            )
            for order, (label, intro) in enumerate(p["steps"], start=1):
                # No video file — upload it on the product page in the admin.
                ProductTutorialStep.objects.update_or_create(
                    product=product,
                    order=order,
                    defaults={
                        "button_label": label,
                        "intro_text": intro,
                        "protect_content": True,
                    },
                )
            result.append(product)
        self.stdout.write(f"• {len(result)} ta mahsulot + bosqichlar OK")
        return result

    def _discounts(self) -> None:
        for d in DISCOUNTS:
            Discount.objects.update_or_create(
                title=d["title"],
                defaults={
                    "percent": d["percent"],
                    "description": d["description"],
                    "promo_code": d["promo_code"],
                    "is_active": True,
                },
            )
        self.stdout.write(f"• {len(DISCOUNTS)} ta chegirma OK")

    def _seller(self, telegram_id: int) -> SellerProfile:
        from apps.users.roles import sync_seller_group

        seller_group = sync_seller_group()
        user, created = User.objects.get_or_create(
            username="seller",
            defaults={"is_staff": True, "email": "seller@example.com"},
        )
        if created:
            user.set_password("seller")
        user.is_staff = True
        user.save()
        user.groups.add(seller_group)
        profile, _ = SellerProfile.objects.update_or_create(
            user=user,
            defaults={
                "telegram_id": telegram_id,
                "display_name": "Demo Sotuvchi",
                "is_active": True,
            },
        )
        self.stdout.write(
            f"• Sotuvchi 'seller/seller' + referal (tg={telegram_id}) OK"
        )
        return profile

    def _sample_user(
        self, telegram_id: int, product: Product, seller: SellerProfile
    ) -> TelegramUser:
        today = timezone.localdate()
        user, _ = TelegramUser.objects.update_or_create(
            telegram_id=telegram_id,
            defaults={
                "username": "demo_user",
                "full_name": "Demo Foydalanuvchi",
                "birth_date": today,  # birthday today → tests birthday task
                "phone_number": "+998901234567",
                "face_condition": TelegramUser.FaceCondition.COMBINED,
                "source": TelegramUser.RegistrationSource.ADMIN,
                "referred_by_seller": seller,
                "registration_status": TelegramUser.RegistrationStatus.COMPLETED,
                "is_active": True,
            },
        )
        UserProduct.objects.get_or_create(user=user, product=product)
        self.stdout.write(f"• Namuna foydalanuvchi (tg={telegram_id}) OK")
        return user

    # Realistic customers so every bonus-program page has something to show:
    # a range of balances (bronze → gold), two of them invited by the main demo
    # user, and one reward already redeemed.
    _DEMO_CUSTOMERS = [
        ("Nilufar Karimova", "nilufar_k", 333333301, "+998901112201", 5),
        ("Sardor Aliyev", "sardor_a", 333333302, "+998901112202", 34),
        ("Dilnoza Yusupova", "dilnoza_y", 333333303, "+998901112203", 12),
        ("Jasur Rahimov", "jasur_r", 333333304, "+998901112204", 3),
    ]

    def _loyalty_demo(self, inviter: TelegramUser, products: list[Product]) -> None:
        from apps.loyalty import services as loyalty
        from apps.loyalty.models import PointsTransaction, Reward

        Reason = PointsTransaction.Reason
        # The bot never messages anyone during a seed run: these are fake chat
        # ids, and the program is only being pre-filled, not announced.
        loyalty.award(
            inviter, Reason.REGISTRATION, reference=f"registration:{inviter.pk}", notify=False
        )

        referred_pks: list[int] = []
        for i, (name, uname, tg, phone, purchases) in enumerate(self._DEMO_CUSTOMERS):
            invited = i < 2  # first two came through the demo user's invite link
            customer, _ = TelegramUser.objects.update_or_create(
                telegram_id=tg,
                defaults={
                    "username": uname,
                    "full_name": name,
                    "phone_number": phone,
                    "face_condition": TelegramUser.FaceCondition.NORMAL,
                    "source": TelegramUser.RegistrationSource.SELF,
                    "registration_status": TelegramUser.RegistrationStatus.COMPLETED,
                    "registered_by": inviter if invited else None,
                    "is_active": True,
                },
            )
            if products:
                UserProduct.objects.get_or_create(
                    user=customer, product=products[i % len(products)]
                )
            loyalty.award(
                customer,
                Reason.REGISTRATION,
                reference=f"registration:{customer.pk}",
                notify=False,
            )
            for n in range(purchases):
                loyalty.award(
                    customer,
                    Reason.PURCHASE,
                    reference=f"seed-purchase:{customer.pk}:{n}",
                    notify=False,
                )
            if invited:
                referred_pks.append(customer.pk)

        # The main demo user is credited for the two friends they brought in.
        for pk in referred_pks:
            loyalty.award(
                inviter, Reason.REFERRAL, reference=f"referral:{pk}", notify=False
            )

        # One reward actually redeemed, so that page isn't empty either.
        top = TelegramUser.objects.filter(telegram_id=self._DEMO_CUSTOMERS[1][2]).first()
        cheapest = Reward.objects.filter(is_active=True).order_by("cost_points").first()
        if top and cheapest:
            try:
                loyalty.redeem(top, cheapest.pk)
            except loyalty.RedeemError:
                pass

        self.stdout.write(
            f"• Bonus demo: {len(self._DEMO_CUSTOMERS)} mijoz, 2 referal, "
            "ball harakatlari + 1 almashtirilgan sovg'a OK"
        )

