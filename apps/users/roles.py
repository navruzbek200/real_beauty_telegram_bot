"""
What a seller is allowed to do.

Permissions are what actually gates the admin, so the role radio on the staff
page has to map onto a real permission set. Keeping that set here — rather than
in whatever state the group happens to be in the database — means the answer to
"what can a seller see?" is readable, and a migration can enforce it.
"""

from __future__ import annotations

from django.contrib.auth.models import Group, Permission

SELLER_GROUP = "Seller"

# (app_label, codename) — a seller runs the counter: they add customers, record
# what those customers bought, and answer them. Everything that changes how the
# bot behaves (settings, templates, discounts) is deliberately absent.
SELLER_PERMISSIONS: list[tuple[str, str]] = [
    ("users", "view_telegramuser"),
    ("users", "add_telegramuser"),
    ("users", "change_telegramuser"),
    # Proxy models carry their own permissions, so the app-users page stays a
    # 403 for sellers unless these are granted alongside the customer ones.
    ("users", "view_appuser"),
    ("users", "change_appuser"),
    ("users", "view_userproduct"),
    ("users", "add_userproduct"),
    ("users", "change_userproduct"),
    ("users", "delete_userproduct"),
    ("products", "view_product"),
    # The monthly top-10 list is a seller's own merchandising call — full
    # control here, unlike the read-only view of the main catalogue above.
    ("products", "view_topproduct"),
    ("products", "add_topproduct"),
    ("products", "change_topproduct"),
    ("products", "delete_topproduct"),
    # Tutorial videos are merchandising content too — the seller uploads and
    # maintains them the same way they curate the top list.
    ("products", "view_producttutorialstep"),
    ("products", "add_producttutorialstep"),
    ("products", "change_producttutorialstep"),
    ("products", "delete_producttutorialstep"),
    # The quiz answers are a selling tool — they say which product this
    # customer's skin actually needs.
    ("analytics", "view_skinquizresult"),
    ("support", "view_supportthread"),
    ("support", "change_supportthread"),
    ("support", "view_supportmessage"),
    ("support", "add_supportmessage"),
    # Orders are the counter's daily bread: the seller confirms, ships and
    # closes them. Creation stays with the customer (Mini App only).
    ("orders", "view_order"),
    ("orders", "change_order"),
]


def sync_seller_group(group_model=Group, permission_model=Permission) -> Group:
    """
    Make the Seller group match SELLER_PERMISSIONS exactly.

    Model classes are injectable so migrations can pass their historical
    versions instead of the live ones.
    """
    group, _ = group_model.objects.get_or_create(name=SELLER_GROUP)
    wanted = permission_model.objects.filter(
        content_type__app_label__in={app for app, _ in SELLER_PERMISSIONS},
        codename__in={codename for _, codename in SELLER_PERMISSIONS},
    )
    # The filter above is a coarse cross-product; keep only real pairs.
    wanted = [
        p
        for p in wanted.select_related("content_type")
        if (p.content_type.app_label, p.codename) in set(SELLER_PERMISSIONS)
    ]
    group.permissions.set(wanted)
    return group
