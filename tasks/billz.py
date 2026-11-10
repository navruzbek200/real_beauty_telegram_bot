import logging

from celery import shared_task
from django.conf import settings

from apps.billz.client import BillzError, BillzHistoryError
from apps.billz.services import sync_billz, deliver_pending
from apps.billz.receipts import deliver_receipts

logger = logging.getLogger(__name__)


@shared_task
def poll_billz():
    if not settings.BILLZ_SECRET_TOKEN:
        return {'enabled': False}
    try:
        result = sync_billz()
    except BillzError as exc:
        # Exception messages deliberately contain no remote bodies or PII.
        logger.warning('%s', exc)
        result = {'error': str(exc),'live_complete':isinstance(exc,BillzHistoryError)}
    if not result.get('busy') and (not result.get('error') or result.get('live_complete')):
        result['receipts_sent']=deliver_receipts()
        result['tutorials_sent'] = deliver_pending()
    return result
