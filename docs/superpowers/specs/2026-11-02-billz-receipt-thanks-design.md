# BILLZ receipt thank-you messages

The user explicitly delegates the design, implementation, testing and production deployment. Build on the existing Django/Celery/PostgreSQL/React application; the attached ntodo directory is a separate Flutter project and is not modified.

## Required outcome

One complete new BILLZ receipt automatically produces one personalized thank-you for its verified Telegram customer. Include the first name and every purchased product/quantity directly from BILLZ. No local catalogue match, tutorial video or manual product assignment is required. Admin edits one reusable message; name/product variables are filled per recipient. Show receipts, products, message state, time and errors in the panel. Existing 7/15-day campaigns get the same real name/product context.

## Approach

Use an explicit unique BILLZ receipt and its existing purchase lines, plus the existing MessageTemplate system. Per-line delivery would send multiple thank-yous and lose receipt context; Mini App orders have shipping/payment semantics and remain separate. Add a prominent BILLZ sales page and rename the old page to Online orders.

## Behavior and constraints

- Match only canonical full phone and Telegram-owned contact proof, active completed customer. Never assign a buyer's purchase to the test admin.
- No added BILLZ data filters. Preserve historical receipts, returns, cancellations, manual entitlements and existing tutorial functionality.
- Activate thank-yous for new sales after deployment. Backfilled existing receipts are historical and remain silent; no bulk retroactive send.
- Mark a receipt ready only after its complete report was read. Partial pagination cannot send an incomplete list.
- Persist pending/sending/sent/failed/unknown state before delivery. Successful Telegram response records message IDs and time; repeat imports and overlapping workers cannot repeat a sent receipt. An uncertain network result/crash is held for review instead of automatically risking a duplicate. Known rejected transient sends retry with backoff.
- Long receipts retain all products by splitting into tracked parts; preserve successful parts on retry. Sending success means accepted by Telegram, not read by the customer.
- Recheck current customer phone, ownership and active receipt immediately before sending. Recipient changes after a send are held, not silently resent to somebody else.
- Editable default thank-you in Uzbek/Russian/English; first_name, product_name/product.name, products_text, purchase_date and order_number available. If admin writes static text alone, automatically include the name and full product list.
- 7/15-day rules stay configurable. Receipt campaigns use every product, including unmapped BILLZ products, with one receipt anchor. Preserve legacy logged campaigns and manual purchase behavior.
- Add staff-readable BILLZ sales and superuser-only template editing/retry. PII remains authenticated; no BILLZ token in frontend, logs or source.

## Verification

Regressions for two products/one receipt without guides, repeated imports/concurrent sends, two independent receipts, unknown delivery, blocked customer, delayed linking, cancellation/correction, long messages, historical silence, placeholders, receipt campaign timing and API permissions. Full local and production PostgreSQL suites, frontend build/lint, fresh review, backed-up deploy, authenticated API and live Telegram test to the previously authorized @nick_lone without changing real buyer ownership.
