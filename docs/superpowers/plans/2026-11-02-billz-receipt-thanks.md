# BILLZ Receipt Thanks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Automatically send one complete, editable thank-you per new BILLZ receipt and expose accurate delivery state in the admin panel.

**Architecture:** Add BillzReceipt linked from existing BillzPurchase rows. Reuse MessageTemplate for purchase_thanks, centralize safe purchase context, keep tutorials independent, and use persistent receipt delivery state/parts for idempotent delivery. Extend current campaigns and React navigation/API patterns.

**Tech Stack:** Existing Django, DRF, Celery, PostgreSQL, Redis, Jinja2, React/TypeScript; no added dependencies.

**Spec:** docs/superpowers/specs/2026-11-02-billz-receipt-thanks-design.md

## Global Constraints

- Keep BILLZ ingestion scope unchanged and preserve all existing records.
- Own-contact proof and exact full phones required before sending personal receipts.
- No retroactive mass messages; cutover timestamp is explicit.
- All products are included regardless of catalogue/video mapping.
- Historical, cancelled and returned sales remain visible; inactive receipts cannot trigger new messages.
- Existing source checkout and production must be hash-checked before edits; back up source/database before deployment.

## Review Focus

- Report failure after the first line must not send a partial receipt.
- Worker crash/network timeout after Telegram accepts a message must not cause a blind duplicate.
- Changing a receipt's customer or a customer's phone must not disclose the old receipt.
- A long list must retain every product and resume safely after a known rejected part.
- A historical backfill failure must not starve already validated new-sales messages.

## Task 1: Receipt model, context and delivery

**Files:** apps/billz/models.py, apps/billz/receipts.py (new), apps/billz/services.py, apps/billz/client.py, apps/billz/migrations/0004_*.py, apps/campaigns/models.py and migration0015, core/purchase_context.py (new), core/telegram.py, tasks/billz.py, tasks/scheduled.py, apps/users/models.py, apps/users/identity.py, tests/test_billz_receipts.py (new), existing affected tests.

**Interfaces:** import_purchase attaches a unique receipt; finalize_receipts(ids, timestamp) validates complete receipt snapshots; deliver_receipts() returns accepted receipt count; purchase_context(user, products, receipt=None) supplies first_name/product aliases and product list.

- [ ] Write and run RED tests for unmapped milk+bread producing one personalized receipt, replay/concurrency, two receipts, historical silence and complete-report readiness.
- [ ] Implement schema/backfill, default template, exact ownership checks, safe rendering/chunking and persistent delivery states. Add error/correction/long-part regressions RED→GREEN.
- [ ] Integrate live-complete polling, keep tutorial sends without a second purchase greeting, and migrate receipt-based delayed campaigns with first_name/product aliases.
- [ ] Run the full test suite and record results; checkpoint in the isolated clone.

## Task 2: Panel API and UI

**Files:** apps/api/views/billz.py and serializers/billz.py (new), apps/api/urls.py, existing campaign serializers/views, apps/users/roles.py, frontend/src/entities/billz/* (new), frontend/src/pages/billz-sales/index.tsx (new), existing navigation/router/order/campaign UI, generated API types, tests/test_billz_receipts.py.

**Interfaces:** staff read /billz-receipts/ and detail; superuser retries confirmed failures; template uses existing message-templates API; preview returns rendered message without delivery.

- [ ] RED→GREEN API tests: all products/status/time, anonymous/nonstaff denial, seller cannot change templates/retry, sent receipt cannot be resent, invalid template rejects save.
- [ ] Add sales list/filter/detail and editable default thank-you with variable help/preview. Show sent, unlinked, inactive, old-history, retry and uncertain states accurately.
- [ ] Rename Mini App orders and link to BILLZ sales; update 7/15-day help/examples. Regenerate API types, build/typecheck and lint.

## Task 3: Review, deployment and live verification

- [ ] Fresh whole-change review; one RED→GREEN fix pass for important findings, full suite green.
- [ ] Hash-check and apply source changes to the supplied Real Beauty folder and server. No changes to ntodo.
- [ ] Back up production source/database, build overlays from current pinned runtime images and local frontend, run the whole suite against isolated production PostgreSQL.
- [ ] Warm-stop workers, apply additive migrations, prove existing customer/purchase counts unchanged, start services and verify HTTPS/authenticated receipt API/preview/status.
- [ ] Test final rendered real receipt to the authorized @nick_lone and verify response; never insert a fake purchase into a real customer's history. Check new automatic job success and remove temporary credentials.
