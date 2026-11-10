from django.apps import AppConfig


class BillzConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.billz'
    verbose_name = 'BILLZ'

    def ready(self):
        from django.db.models.signals import post_migrate
        from apps.users.apps import _sync_seller_group
        post_migrate.connect(_sync_seller_group, sender=self)
