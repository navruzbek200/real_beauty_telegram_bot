"""Read-only BILLZ public API. No customer/sale write routes are exposed."""
import hashlib
import time

import requests
from django.conf import settings
from django.core.cache import cache

BASE_URL = 'https://api-admin.billz.ai'
PLATFORM_ID = '7d4a4c38-dd84-4902-b744-0488b80a4c01'


class BillzError(Exception):
    """Deliberately excludes remote bodies, credentials and customer data."""


class BillzHistoryError(BillzError):
    """Live sales were verified; only the older backfill failed."""


class BillzClient:
    def __init__(self):
        self.secret = settings.BILLZ_SECRET_TOKEN
        if not self.secret:
            raise BillzError('BILLZ_SECRET_TOKEN sozlanmagan.')
        self.token_key = 'billz:token:' + hashlib.sha256(self.secret.encode()).hexdigest()
        self.last_request = 0.0

    def _request(self, method, path, **kwargs):
        for attempt in range(3):
            time.sleep(max(0, .55 - (time.monotonic() - self.last_request)))
            self.last_request = time.monotonic()
            try:
                response = requests.request(method, BASE_URL + path, timeout=(5, 30), allow_redirects=False, **kwargs)
            except requests.RequestException:
                if attempt == 2:
                    raise BillzError('BILLZ tarmoq xatosi.') from None
                time.sleep(2 ** attempt)
                continue
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue
            return response

    def _token(self):
        token = cache.get(self.token_key)
        if token:
            return token
        response = self._request('POST', '/v1/auth/login', json={'secret_token': self.secret})
        if response.status_code != 200:
            raise BillzError(f'BILLZ login HTTP {response.status_code}.')
        try:
            data = response.json()['data']
            token = data['access_token']
            ttl = max(1, int(data['expires_in']) - 120)
            if not isinstance(token, str) or not token:
                raise ValueError
        except (ValueError, KeyError, TypeError):
            raise BillzError('BILLZ login javobi noto‘g‘ri.') from None
        cache.set(self.token_key, token, ttl)
        return token

    def _get(self, path, params):
        for attempt in range(2):
            headers = {'Authorization': 'Bearer ' + self._token(), 'platform-id': PLATFORM_ID}
            response = self._request('GET', path, headers=headers, params=params)
            if response.status_code == 401 and attempt == 0:
                cache.delete(self.token_key)
                continue
            if response.status_code != 200:
                raise BillzError(f'BILLZ {path} HTTP {response.status_code}.')
            try:
                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError
                return data
            except ValueError:
                raise BillzError('BILLZ JSON javobi noto‘g‘ri.') from None

    def _pages(self, path, field, **params):
        page = 1
        received = 0
        while True:
            data = self._get(path, {**params, 'page': page, 'limit': 20})
            rows = data.get(field) or []
            count = data.get('count')
            if field not in data or not isinstance(rows, list) or not isinstance(count, int) or count < 0:
                raise BillzError('BILLZ sahifalash javobi noto‘g‘ri.')
            if any(not isinstance(row, dict) for row in rows):
                raise BillzError('BILLZ yozuv shakli noto‘g‘ri.')
            yield from rows
            received += len(rows)
            # BILLZ can overstate count (observed: 46 vs 45 rows). An explicit
            # empty page ends the report even when that total is stale.
            if not rows or received >= count:
                return
            page += 1

    def shops(self):
        wanted = settings.BILLZ_SHOP_IDS
        shops = [shop for shop in self._pages('/v1/shop', 'shops') if not shop.get('deleted_at')]
        if wanted:
            shops = [shop for shop in shops if shop['id'] in wanted]
            if {shop['id'] for shop in shops} != set(wanted):
                raise BillzError('BILLZ_SHOP_IDS ichida mavjud bo‘lmagan filial bor.')
        if not shops:
            raise BillzError('BILLZ hisobida ruxsat berilgan filial topilmadi.')
        return shops

    def purchases(self, shop_id, start, end):
        if not 0 <= (end - start).days <= 364:
            raise BillzError('BILLZ sana oralig‘i 365 kundan oshmasligi kerak.')
        return self._pages('/v1/customer-purchases-table', 'purchases', shop_ids=shop_id, start_date=start.isoformat(), end_date=end.isoformat(), with_customers='true', group_without_shops='false', price_type=0, currency='UZS')

    def is_cancelled(self, order_id):
        data = self._get('/v2/order/' + order_id, {})
        if data.get('id') != order_id or not isinstance(data.get('deleted'), bool):
            raise BillzError('BILLZ chek holati javobi noto‘g‘ri.')
        return data['deleted']
