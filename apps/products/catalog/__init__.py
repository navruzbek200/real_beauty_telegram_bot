"""
The shop's real catalogue: photo, trilingual name and description per product.

Kept as plain data next to `assets/catalog/` (the shop's own studio shots) so
`manage.py sync_catalog` can be re-run on every deploy without a migration.

The rule the sync obeys — and the reason this file only ever *adds* — is that
the shop edits product text and prices in the admin panel. A seed that
overwrote them would silently undo that work on the next deploy, so an entry
here fills a field only when the database's is still empty, and prices are
never touched at all.
"""

from __future__ import annotations

from apps.products.catalog.doclab import DOCLAB
from apps.products.catalog.merikit import MERIKIT
from apps.products.catalog.other import OTHER
from apps.products.catalog.ronas import RONAS

CATALOG: list[dict] = [*MERIKIT, *DOCLAB, *RONAS, *OTHER]

__all__ = ["CATALOG"]
