"""English strings — mirrors every key in `uz.py`."""

from __future__ import annotations

STRINGS: dict[str, str] = {
    # ------------------------------------------------------------------ menu
    "menu.ingredients": "🧪 Ingredients we study",
    "menu.catalog": "🛍 Products",
    "menu.top": "🔥 Top products this month",
    "menu.feedback": "⭐️ Rate a product",  # legacy label kept for MenuText matching
    "menu.quiz_retake": "🔄 Retake the skin test",
    "menu.support": "✍️ Question / Request",
    "menu.discounts": "🎁 Discounts",
    "menu.bonus": "💎 My bonuses",
    "menu.profile": "👤 Profile",
    "menu.face_analysis": "Face analysis",
    "menu.help": "ℹ️ Help",
    "menu.legacy_tutorials": "📚 Tutorials",
    "menu.legacy_feedback": "💬 Leave feedback",
    "menu.legacy_tips": "💡 Tips",
    "menu.opened": "Main menu. Pick a section 👇",
    # -------------------------------------------------------------- language
    "lang.choose": (
        "🌐 <b>Tilni tanlang / Выберите язык / Choose a language</b>\n\n"
        "Every message and button in the bot will use the language you pick."
    ),
    "lang.changed": "✅ Language changed. Use the menu 👇",
    "lang.button": "🌐 Change language",
    # ---------------------------------------------------------- registration
    "reg.greeting_self": (
        "👋 Welcome to <b>Real Beauty</b>!\n\n"
        "To register, please type your full name."
    ),
    "reg.greeting_admin": (
        "👋 <b>{admin_name}</b> will help you register.\n\n"
        "Please type your full name."
    ),
    "reg.ask_name": "Please type your full name.",
    "reg.name_short": "That name is too short. Please type your full name.",
    "reg.name_invalid": "Names should contain letters only. Please try again.",
    "reg.ask_birth": "📅 What is your date of birth? (dd.mm.yyyy)",
    "reg.invalid_date": (
        "❌ That date isn't valid. Use <b>dd.mm.yyyy</b> "
        "(for example: 25.12.1995)."
    ),
    "reg.date_future": "❌ A birth date can't be in the future. Please try again.",
    "reg.date_old": "❌ That date looks too far back. Please check and try again.",
    "reg.ask_phone": "📱 What is your phone number?",
    "reg.ask_phone_again": "Please send or type your phone number.",
    "reg.invalid_phone": (
        "❌ That number isn't valid. For example: <b>+998 90 123 45 67</b>\n"
        "Or share your contact with the button below."
    ),
    "reg.contact_not_yours": (
        "❌ That's somebody else's contact. Please send your own number."
    ),
    "reg.share_contact": "📱 Share contact",
    "reg.saved_fallback": "✅ Registration complete! Welcome to Real Beauty.",
    "reg.error": "Something went wrong while saving. Please press /start again.",
    "reg.invalid_ref": "That referral link is invalid. You can register on your own.",
    # -------------------------------------------------------------- account
    "user.welcome_back": (
        "👋 Great to see you again, <b>{name}</b>!\n\n"
        "Your details are saved. Use the menu 👇"
    ),
    "user.disabled": (
        "⛔️ Your account is temporarily inactive.\n\n"
        "If you have questions, please contact our shop."
    ),
    "user.not_registered": "Please press /start and register first.",
    # -------------------------------------------------------- app login
    "applogin.confirm_prompt": (
        "📱 <b>{name}</b>, you're requesting to sign in to the mobile app with "
        "this Telegram account.\n\nConfirm?"
    ),
    "applogin.confirm_button": "✅ Confirm",
    "applogin.cancel_button": "❌ Cancel",
    "applogin.confirmed": "✅ Confirmed. Go back to the app and continue.",
    "applogin.cancelled": "❌ Sign-in cancelled.",
    "applogin.expired": "⌛️ This link expired or is invalid. Try again in the app.",
    "applogin.error": "Something went wrong. Try again in the app.",
    # -------------------------------------------------------- face analysis
    "faceanalysis.ask_photo": "🤳 Send one selfie where your face is clearly visible.",
    "faceanalysis.no_face": (
        "😕 No face was detected in that photo (or more than one). "
        "Please send another photo with your face clearly visible."
    ),
    "faceanalysis.success": (
        "🎉 <b>{full_name}</b>, welcome to the Real Beauty family!\n\n"
        "We've analyzed your face. Thank you for choosing Real Beauty!\n\n"
        "If you have questions — tap the «✍️ Question / Request» button below, "
        "our team will reply 👇"
    ),
    "faceanalysis.error": "Something went wrong. Please try again.",
    # ----------------------------------------------------------- skin / quiz
    "skin.know_question": (
        "🧴 <b>Do you know your skin type?</b>\n\n"
        "If you do, we'll set it right away. If not, we'll find it together "
        "with 10 short questions — about a minute."
    ),
    "skin.know_yes": "✅ Yes, I know it",
    "skin.know_no": "🔍 No, help me find out",
    "skin.pick": "Pick your skin type 👇",
    "skin.type.dry": "Dry",
    "skin.type.oily": "Oily",
    "skin.type.combined": "Combination",
    "skin.type.normal": "Normal",
    "skin.type.sensitive": "Sensitive",
    "quiz.intro": (
        "🔍 <b>Let's find your skin type</b>\n\n"
        "We'll ask 10 simple questions. Rate each one <b>from 0 to 5</b> — "
        "0 means \"not at all\", 5 means \"very much\".\n\n"
        "At the end you get your skin type and a care plan made for you. Ready?"
    ),
    "quiz.start": "🚀 Let's go",
    "quiz.progress": "Question {index}/{total}",
    "quiz.scale_hint": "0️⃣ {low}   ·   5️⃣ {high}",
    "quiz.back": "⬅️ Back",
    "quiz.result_header": "✨ <b>Your analysis is ready!</b>",
    "quiz.result_type": "🧴 Your skin type: <b>{skin_type}</b>",
    "quiz.recs_header": "📋 <b>Recommendations for you</b>",
    "quiz.done_footer": (
        "These recommendations are saved in your profile. Any questions — tap "
        "«✍️ Question / Request»."
    ),
    "quiz.retake": "🔄 Retake the quiz",
    "quiz.q1": (
        "One hour after washing your face, with no cream applied, how does "
        "your skin feel?"
    ),
    "quiz.q1.opt0": "0 · Very tight and dry",
    "quiz.q1.opt1": "1 · Slightly dry",
    "quiz.q1.opt2": "2 · Dry cheeks, oily T-zone",
    "quiz.q1.opt3": "3 · Balanced",
    "quiz.q1.opt4": "4 · Gets oily",
    "quiz.q1.opt5": "5 · Gets oily very fast",
    "quiz.q2": "How visible are the pores on your face?",
    "quiz.q2.low": "not visible at all",
    "quiz.q2.high": "very visible",
    "quiz.q3": "How often do you get allergic reactions on your skin?",
    "quiz.q3.low": "never had one",
    "quiz.q3.high": "very often",
    "quiz.q4": "How often do breakouts (pimples) appear?",
    "quiz.q4.low": "never",
    "quiz.q4.high": "all the time",
    "quiz.q5": "How many blackheads do you have?",
    "quiz.q5.low": "none at all",
    "quiz.q5.high": "a great many",
    "quiz.q6": "How many whiteheads (milia) do you have?",
    "quiz.q6.low": "none at all",
    "quiz.q6.high": "a great many",
    "quiz.q7": "Is your skin prone to dark spots and pigmentation?",
    "quiz.q7.low": "not at all",
    "quiz.q7.high": "very prone",
    "quiz.q8": "How visible are fine lines around your eyes?",
    "quiz.q8.low": "not visible at all",
    "quiz.q8.high": "very visible",
    "quiz.q9": "Do you have dark circles under your eyes?",
    "quiz.q9.low": "none at all",
    "quiz.q9.high": "very dark",
    "quiz.q10": (
        "How much firmness has your facial skin lost (is sagging noticeable)?"
    ),
    "quiz.q10.low": "none at all",
    "quiz.q10.high": "a lot, plenty of sagging",
    "rec.base.dry": (
        "💧 <b>Dry skin</b>\n"
        "• Gentle, non-foaming cleanser — sulfate free\n"
        "• Alcohol-free toner, moisturiser straight after\n"
        "• Apply cream to <i>damp</i> skin — it locks the water in\n"
        "• A richer cream or facial oil at night\n"
        "• SPF 30+ every morning — no exceptions"
    ),
    "rec.base.oily": (
        "🫧 <b>Oily skin</b>\n"
        "• Cleanse twice a day with a light gel/foam — no more than that\n"
        "• A niacinamide or zinc serum\n"
        "• Light, non-comedogenic moisturiser — oily skin needs water too\n"
        "• BHA (salicylic acid) once or twice a week\n"
        "• SPF — light, gel formula"
    ),
    "rec.base.normal": (
        "🌿 <b>Normal skin</b>\n"
        "• Keep the balance: cleanse → tone → moisturise\n"
        "• One gentle exfoliation a week is plenty\n"
        "• An antioxidant (vitamin C) in the morning\n"
        "• Switch cream with the season\n"
        "• SPF 30+ every morning"
    ),
    "rec.base.combined": (
        "⚖️ <b>Combination skin</b>\n"
        "• Light products on the T-zone (forehead, nose, chin), richer cream "
        "on the cheeks\n"
        "• Gentle exfoliation once a week\n"
        "• Toner over the whole face, moisturiser by zone\n"
        "• Avoid heavy, greasy creams\n"
        "• Don't skip SPF in the morning"
    ),
    "rec.base.sensitive": (
        "🌸 <b>Sensitive skin</b>\n"
        "• Patch-test every new product on your wrist for 24 hours\n"
        "• Choose fragrance-free formulas\n"
        "• Skip scrubs — a mild chemical exfoliant is kinder\n"
        "• Fewer products is better: a simple 3–4 step routine\n"
        "• Mineral (physical) SPF suits you best"
    ),
    "rec.P0": (
        "🕳 <b>Enlarged pores</b>\n"
        "Niacinamide (5%) plus BHA twice a week tightens pores. Daily SPF is "
        "essential — sun damage makes pores look larger."
    ),
    "rec.S": (
        "🌡 <b>Sensitivity / allergies</b>\n"
        "Simplify your routine: cleanser + moisturiser + SPF. Look for "
        "centella, panthenol and ceramides; pause acids and retinoids for now."
    ),
    "rec.Bh": (
        "⚫️ <b>Blackheads</b>\n"
        "Salicylic acid (BHA) two or three times a week. Don't squeeze them — "
        "that leaves marks and inflammation."
    ),
    "rec.Wh": (
        "⚪️ <b>Whiteheads (milia)</b>\n"
        "Mild AHA/BHA and adapalene help. Swap heavy, greasy creams for a "
        "light gel."
    ),
    "rec.P": (
        "🟤 <b>Spots and pigmentation</b>\n"
        "Vitamin C in the morning, niacinamide or alpha-arbutin at night. "
        "SPF 50 is the strongest anti-pigmentation tool there is."
    ),
    "rec.Ew": (
        "👁 <b>Fine lines around the eyes</b>\n"
        "An eye cream with peptides or low-dose retinol at night. Pat it into "
        "that thin skin gently with a fingertip."
    ),
    "rec.Ed": (
        "🌙 <b>Dark circles</b>\n"
        "A caffeine eye serum, a cold compress and a steady sleep schedule. "
        "Vitamin K and niacinamide support circulation."
    ),
    "rec.W": (
        "🪢 <b>Loss of firmness</b>\n"
        "Retinoid at night, peptides + SPF in the morning. Facial massage and "
        "exercises add to the effect."
    ),
    "rec.Ao": (
        "🔴 <b>Breakouts (oily skin)</b>\n"
        "BHA plus benzoyl peroxide or adapalene. A light, oil-free "
        "moisturiser. If it persists, see a dermatologist."
    ),
    "rec.Ad": (
        "🔴 <b>Breakouts (dry / sensitive skin)</b>\n"
        "Avoid harsh drying products. Azelaic acid and niacinamide work "
        "gently and keep your skin barrier intact."
    ),
    # ------------------------------------------------------------- products
    "purchase.thanks": (
        "🛍 Thank you for your purchase!\n\n"
        "Below is the guide on how to use it. We'll ask about your result in "
        "a week 😊"
    ),
    "product.none": (
        "🎓 <b>Video lessons are coming soon!</b>\n\n"
        "They are being prepared right now. As soon as they are ready they "
        "will appear here — stay tuned 🌸"
    ),
    "tutorial.intro_fallback": "📘 Guide for <b>{product}</b>",
    "tutorial.video_soon": "⏳ The video for this step is coming soon.",
    "tutorial.no_steps": "⏳ Video lessons for this product are coming soon.",
    "tutorial.step_not_found": "Step not found.",
    "catalog.header": "🛍 <b>Our products:</b>",
    "catalog.empty": "The catalogue is empty for now. We'll fill it soon!",
    "catalog.footer": (
        "📍 Visit our shop or write through «✍️ Question / Request» — "
        "we'll help you buy."
    ),
    "top.header": "🔥 <b>Top products of {month}</b>",
    "top.empty": (
        "This month's top list isn't filled in yet. We'll announce it soon — "
        "stay tuned!"
    ),
    "top.footer": (
        "🏷 These were the most-chosen products this month. Any questions — "
        "tap «✍️ Question / Request»."
    ),
    "top.rank": "#{rank}",
    "top.price": "💵 <b>{current} UZS</b>",
    "top.price_discount": "💸 <s>{old} UZS</s>  ➜  <b>{current} UZS</b>  (-{percent}%)",
    # --------------------------------------------------------- product browser
    "catalog.list_header": (
        "🛍 <b>Products</b> · {total}\n"
        "Pick a product to see the details 👇"
    ),
    "top.list_header": (
        "🔥 <b>{month} — top products</b>\n"
        "Pick one to see the details 👇"
    ),
    "tutorial.list_header": (
        "🎓 <b>Guides</b>\n"
        "Pick a product to open its video lessons 👇"
    ),
    "catalog.gone": "This product is no longer available.",
    "browse.prev": "◀️ Prev",
    "browse.next": "Next ▶️",
    "browse.counter": "{page}/{total}",
    "browse.back": "⬅️ Back to list",
    # -------------------------------------------------------------- support
    "webapp.open": "🛍 Open the shop",
    "webapp.intro": (
        "🛍 <b>Product shop</b>\n\n"
        "All products, prices and discounts — in a convenient app. "
        "Tap the button below to open 👇"
    ),
    "webapp.ask_product": (
        "🛍 Write your question about <b>{product}</b> 👇\n"
        "Our team will reply right here."
    ),
    "pay.unavailable": "This order can no longer be paid for. Please message us.",
    "order.location_saved": (
        "✅ Thank you! The location is saved to order <b>#{id}</b>.\n"
        "The courier will come to exactly that spot 🚕"
    ),
    "order.location_unexpected": (
        "No order is waiting for a location right now. Use the menu 👇"
    ),
    "learn.open": "🎓 Open the lessons",
    "learn.intro": (
        "🎓 <b>Video lessons</b>\n\n"
        "Guides and video lessons for your products — in a convenient app. "
        "Pick a lesson and the video opens right here in the chat 👇"
    ),
    "support.ask": (
        "✍️ Write your question or request.\n\n"
        "You can send text or a photo — our team answers right here.\n"
        "Use the buttons below to go back to the menu."
    ),
    "support.empty": "Please write some text or send a photo.",
    "support.saved": (
        "✅ Got it! Our team will answer here shortly.\n\n"
        "Want to add more — just keep writing 👇"
    ),
    "support.save_error": "Couldn't save your request. Please try again later.",
    "support.reply_btn": "✍️ Write a reply",
    "support.rate_limited": (
        "⏳ That's a lot of messages at once. Please wait a moment and try again."
    ),
    "support.no_unanswered": "✅ No unanswered requests.",
    "support.unanswered_header": "🔁 Re-sending unanswered requests: {count}",
    # ------------------------------------------------------------ discounts
    "discount.none": "No active discounts right now.",
    "discount.header": "🎁 <b>Active discounts:</b>",
    "discount.until": "⏳ until {date}",
    # -------------------------------------------------------------- profile
    "profile.template": (
        "👤 <b>Your profile</b>\n\n"
        "Name: {full_name}\n"
        "Phone: {phone}\n"
        "Date of birth: {birth_date}\n"
        "Skin type: {face}"
    ),
    # ------------------------------------------------------------- fallback
    "fallback.unknown": (
        "I didn't catch that 🤔\n\n"
        "Pick a section from the menu below. If you have a question, tap "
        "«✍️ Question / Request»."
    ),
    "fallback.stale_button": "That button is out of date. Press /menu.",
    # ----------------------------------------------------------------- help
    "help.text": (
        "ℹ️ <b>Real Beauty bot</b>\n\n"
        "• 🛍 Products — the shop app: catalogue, 🔥 TOP picks and 🎓 video "
        "lessons (the app's «Lessons» tab)\n"
        "• 🎁 Discounts — current promotions and promo codes\n"
        "• 💎 My bonuses — your points, tier and rewards\n"
        "• 👤 Profile — your details, skin test and language setting\n"
        "• ✍️ Question / Request — live chat with our team\n\n"
        "Send /menu to open the menu."
    ),
    # --------------------------------------------------------------- seller
    "seller.only": "⛔️ This command is for sellers only.",
    "seller.link": "🔗 Your referral link:\n<code>{link}</code>",
    "admin.user_started": (
        "🆕 A new user pressed start through your referral link.\n"
        "Telegram ID: <code>{telegram_id}</code>\n"
        "Status: waiting to be filled in."
    ),
    "admin.user_registered": "✅ <b>{full_name}</b> completed registration.",
    # ------------------------------------------------------- bot command menu
    # ------------------------------------------------------- loyalty / bonus
    "loyalty.disabled": "💎 The bonus program is currently off. It'll be back soon!",
    "loyalty.summary": (
        "💎 <b>My bonuses</b>\n\n"
        "🏅 Tier: <b>{tier}</b> · {cashback}% cashback\n"
        "✨ Balance: <b>{balance}</b> points\n"
        "📈 Lifetime earned: {lifetime} points"
    ),
    "loyalty.next_tier": "\n⬆️ {remaining} points to reach <b>{tier}</b>",
    "loyalty.max_tier": "\n🎉 You're at the top tier — amazing!",
    "loyalty.invite_block": (
        "\n\n🎁 <b>Invite a friend</b>\n"
        "Earn <b>+{points} points</b> for every friend who registers!\n"
        "Your link:\n<code>{link}</code>"
    ),
    "loyalty.share_button": "📤 Share with a friend",
    "loyalty.share_text": (
        "✨ Join the Real Beauty bot — skincare tailored to your skin type, "
        "discounts and bonuses are waiting for you! 💎"
    ),
    "loyalty.rewards_button": "🎁 Rewards",
    "loyalty.rewards_header": (
        "🎁 <b>Rewards</b>\n\n"
        "Trade your points for rewards. Balance: <b>{balance}</b> points 👇"
    ),
    "loyalty.rewards_empty": "No rewards yet. We'll add some soon!",
    "loyalty.reward_line": "• <b>{title}</b> — {cost} points",
    "loyalty.redeem_ok": (
        "✅ Congratulations! Your reward is ready.\n\n"
        "Show this in store:\n🔑 <code>{code}</code>"
    ),
    "loyalty.redeem_not_enough": "😔 Not enough points. Keep earning or invite a friend!",
    "loyalty.redeem_unavailable": "😔 This reward isn't available right now.",
    "loyalty.referral_joined": (
        "🎉 <b>Your friend joined!</b>\n"
        "You earned <b>+{points} points</b>. Thank you! 💎"
    ),
    "loyalty.earned": "✨ You earned <b>+{points} points</b> ({reason}).\nTotal: {total} points 💎",
    "loyalty.tier_up": "🎉 Congratulations! You reached the <b>{tier}</b> tier — {cashback}% cashback!",
    "loyalty.reason.registration": "registration",
    "loyalty.reason.purchase": "purchase",
    "loyalty.reason.feedback": "review",
    "loyalty.reason.progress": "result photo",
    "loyalty.reason.referral": "friend referral",
    "loyalty.reason.birthday": "birthday",
    "loyalty.reason.quiz": "skin quiz",
    "loyalty.reason.redeem": "reward",
    "loyalty.reason.manual": "adjustment",
    "loyalty.tier.bronze": "Bronze",
    "loyalty.tier.silver": "Silver",
    "loyalty.tier.gold": "Gold",
    "loyalty.tier.platinum": "Platinum",
    "cmd.start": "Start the bot",
    "cmd.menu": "Main menu",
    "cmd.help": "Help",
    "cmd.language": "Change language",
}
