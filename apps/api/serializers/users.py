from __future__ import annotations

from django.contrib.auth.models import User
from rest_framework import serializers

from apps.users.models import AppUser, SellerProfile, TelegramUser, UserProduct
from apps.billz.models import BillzPurchase


class BillzPurchaseSerializer(serializers.ModelSerializer):
    mapping_id = serializers.CharField(source='item_id', read_only=True)
    has_tutorial = serializers.SerializerMethodField()

    def get_has_tutorial(self, obj) -> bool:
        product = obj.item.product
        return bool(product and any(step.has_video for step in product.tutorial_steps.all()))

    class Meta:
        model = BillzPurchase
        fields = ['id', 'order_number', 'product_name', 'purchased_at', 'quantity', 'returned_quantity', 'active', 'cancelled', 'historical', 'has_tutorial', 'mapping_id']
        read_only_fields = fields


class UserProductSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    is_billz = serializers.SerializerMethodField()

    def get_is_billz(self, obj) -> bool:
        return not obj.auto_messages_enabled

    class Meta:
        model = UserProduct
        fields = [
            "id",
            "user",
            "product",
            "product_name",
            "purchased_at",
            "week1_sent",
            "week2_sent",
            "is_billz",
        ]
        read_only_fields = ["purchased_at", "week1_sent", "week2_sent"]


class TelegramUserSerializer(serializers.ModelSerializer):
    is_linked = serializers.BooleanField(read_only=True)
    purchases = UserProductSerializer(source="userproduct_set", many=True, read_only=True)
    billz_purchases = BillzPurchaseSerializer(many=True, read_only=True)

    class Meta:
        model = TelegramUser
        fields = [
            "id",
            "telegram_id",
            "username",
            "full_name",
            "birth_date",
            "phone_number",
            "phone_verified",
            "language",
            "face_condition",
            "photo",
            "registered_by",
            "referred_by_seller",
            "source",
            "registration_status",
            "is_active",
            "created_at",
            "registered_at",
            "is_linked",
            "purchases",
            "billz_purchases",
        ]
        read_only_fields = [
            "telegram_id",
            "phone_verified",
            "source",
            "registration_status",
            "created_at",
            "registered_at",
        ]

    def validate_full_name(self, value: str) -> str:
        if "<" in value or ">" in value:
            raise serializers.ValidationError("Ismda < yoki > belgisi bo'lmasin.")
        return value

    def validate_username(self, value: str) -> str:
        return (value or "").lstrip("@").strip()

    def validate_phone_number(self, value: str) -> str:
        """
        Store the same canonical +998XXXXXXXXX the bot stores.

        Staff type a number every imaginable way ("90 123 45 67",
        "998901234567"); the bot always saves Telegram's contact in canonical
        form. Without normalising here too, the CRM row and the bot row for
        one person never match on `phone_tail`, so the customer opens the bot
        and gets a second, empty card instead of the one the shop just filled
        in.
        """
        normalized = TelegramUser.normalize_phone(value)
        if normalized is None:
            raise serializers.ValidationError(
                "Raqam noto'g'ri. O'zbekiston uchun: 90 123 45 67. "
                "Boshqa davlat uchun kod bilan: +7 916 123 45 67."
            )
        duplicate = TelegramUser.objects.filter(phone_number=normalized)
        if self.instance:duplicate=duplicate.exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise serializers.ValidationError('Bu telefon raqamiga mijoz allaqachon mavjud. Mavjud kartadan foydalaning.')
        return normalized


class AppUserSerializer(serializers.ModelSerializer):
    is_linked = serializers.BooleanField(read_only=True)
    validate_phone_number = TelegramUserSerializer.validate_phone_number

    class Meta:
        model = AppUser
        fields = [
            "id",
            "full_name",
            "phone_number",
            "registration_status",
            "is_linked",
            "created_at",
        ]
        read_only_fields = ["registration_status", "created_at"]


class SellerProfileSerializer(serializers.ModelSerializer):
    invite_link = serializers.CharField(read_only=True)

    class Meta:
        model = SellerProfile
        fields = ["telegram_id", "display_name", "is_active", "invite_link"]


class StaffSerializer(serializers.ModelSerializer):
    """Staff = the auth.User proxy; role/seller_profile mirror the admin's StaffForm."""

    ROLE_ADMIN = "admin"
    ROLE_SELLER = "seller"

    role = serializers.ChoiceField(choices=[ROLE_ADMIN, ROLE_SELLER])
    seller_profile = SellerProfileSerializer(required=False, allow_null=True)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "is_active",
            "role",
            "seller_profile",
            "password",
        ]

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is None:
            fields["password"].required = True
        return fields

    def to_representation(self, instance: User) -> dict:
        # Not calling super(): the declared `role` field has no matching model
        # attribute, so DRF's default field-by-field lookup would AttributeError
        # on it before this method ever gets a chance to compute it.
        data = {
            "id": instance.id,
            "username": instance.username,
            "first_name": instance.first_name,
            "last_name": instance.last_name,
            "is_active": instance.is_active,
            "role": self.ROLE_ADMIN if instance.is_superuser else self.ROLE_SELLER,
        }
        try:
            data["seller_profile"] = SellerProfileSerializer(instance.seller_profile).data
        except SellerProfile.DoesNotExist:
            data["seller_profile"] = None
        return data

    def create(self, validated_data: dict) -> User:
        role = validated_data.pop("role")
        profile_data = validated_data.pop("seller_profile", None)
        password = validated_data.pop("password")
        user = User(**validated_data, is_staff=True, is_superuser=role == self.ROLE_ADMIN)
        user.set_password(password)
        user.save()
        self._sync_role(user, role)
        if profile_data:
            SellerProfile.objects.create(user=user, **profile_data)
        return user

    def update(self, instance: User, validated_data: dict) -> User:
        role = validated_data.pop("role", None)
        profile_data = validated_data.pop("seller_profile", None)
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        if role is not None:
            instance.is_superuser = role == self.ROLE_ADMIN
        instance.save()
        if role is not None:
            self._sync_role(instance, role)
        if profile_data is not None:
            SellerProfile.objects.update_or_create(user=instance, defaults=profile_data)
        return instance

    @staticmethod
    def _sync_role(user: User, role: str) -> None:
        from apps.users.roles import sync_seller_group

        group = sync_seller_group()
        if role == StaffSerializer.ROLE_ADMIN:
            user.groups.remove(group)
        else:
            user.groups.add(group)
