from __future__ import annotations

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView
from rest_framework.routers import DefaultRouter

from apps.api.views.analytics import SkinQuizResultViewSet
from apps.api.views.auth import (
    CheckSessionView,
    InitSessionView,
    LoginView,
    MeView,
    RefreshView,
)
from apps.api.views.bot_settings import DiscountViewSet, GlobalSettingsView
from apps.api.views.loyalty import LoyaltySettingsView, RewardViewSet
from apps.api.views.orders import OrderViewSet
from apps.api.views.webapp import (
    WebAppCatalogView,
    WebAppLessonsView,
    WebAppOrderView,
)
from apps.api.views.campaigns import (
    AutoMessageViewSet,
    BroadcastViewSet,
    MessageTemplateViewSet,
)
from apps.api.views.products import ProductTutorialStepViewSet, ProductViewSet, TopProductViewSet
from apps.api.views.support import (
    SupportAdminViewSet,
    SupportMessageViewSet,
    SupportSettingsTestConnectionView,
    SupportSettingsView,
    SupportThreadViewSet,
)
from apps.api.views.users import AppUserViewSet, StaffViewSet, TelegramUserViewSet, UserProductViewSet

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("top-products", TopProductViewSet, basename="top-product")
router.register("product-tutorial-steps", ProductTutorialStepViewSet, basename="product-tutorial-step")
router.register("customers", TelegramUserViewSet, basename="customer")
router.register("app-users", AppUserViewSet, basename="app-user")
router.register("user-products", UserProductViewSet, basename="user-product")
router.register("staff", StaffViewSet, basename="staff")
router.register("message-templates", MessageTemplateViewSet, basename="message-template")
router.register("auto-messages", AutoMessageViewSet, basename="auto-message")
router.register("broadcasts", BroadcastViewSet, basename="broadcast")
router.register("discounts", DiscountViewSet, basename="discount")
router.register("rewards", RewardViewSet, basename="reward")
router.register("skin-quiz-results", SkinQuizResultViewSet, basename="skin-quiz-result")
router.register("support-threads", SupportThreadViewSet, basename="support-thread")
router.register("support-messages", SupportMessageViewSet, basename="support-message")
router.register("support-admins", SupportAdminViewSet, basename="support-admin")
router.register("orders", OrderViewSet, basename="order")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="api_login"),
    path("auth/refresh/", RefreshView.as_view(), name="api_refresh"),
    path("auth/me/", MeView.as_view(), name="api_me"),
    path("auth/init-session/", InitSessionView.as_view(), name="api_init_session"),
    path(
        "auth/check-session/<str:session_token>/",
        CheckSessionView.as_view(),
        name="api_check_session",
    ),
    path("settings/global/", GlobalSettingsView.as_view(), name="api_global_settings"),
    path(
        "settings/rewards/",
        LoyaltySettingsView.as_view(),
        name="api_rewards_settings",
    ),
    path("settings/support/", SupportSettingsView.as_view(), name="api_support_settings"),
    path(
        "settings/support/test-connection/",
        SupportSettingsTestConnectionView.as_view(),
        name="api_support_test_connection",
    ),
    path("webapp/catalog/", WebAppCatalogView.as_view(), name="api_webapp_catalog"),
    path("webapp/lessons/", WebAppLessonsView.as_view(), name="api_webapp_lessons"),
    path("webapp/orders/", WebAppOrderView.as_view(), name="api_webapp_orders"),
    path("schema/", SpectacularAPIView.as_view(), name="api_schema"),
    path("", include(router.urls)),
]
