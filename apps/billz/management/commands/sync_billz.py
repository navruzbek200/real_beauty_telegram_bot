from django.core.management.base import BaseCommand, CommandError

from apps.billz.client import BillzClient, BillzError
from apps.billz.services import sync_billz
from apps.billz.models import BillzSyncState


class Command(BaseCommand):
    help = 'BILLZ mijozlari va xaridlarini o‘qish; Telegram xabarlari bu buyruqdan yuborilmaydi.'

    def add_arguments(self, parser):
        parser.add_argument('--check', action='store_true', help='Kalit va filiallarni yozmasdan tekshirish.')
        parser.add_argument('--history', action='store_true', help='Barcha eski davrlarni tugatguncha yuklash.')

    def handle(self, *args, **options):
        try:
            if options['check']:
                self.stdout.write(f"BILLZ ulandi: {len(BillzClient().shops())} ta filial.")
                return
            while True:
                result = sync_billz()
                self.stdout.write(str(result))
                if result.get('busy') or not options['history'] or BillzSyncState.objects.get(pk=1).history_complete:
                    return
        except (BillzError, ValueError) as exc:
            raise CommandError(str(exc)) from None
