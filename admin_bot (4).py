import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

import database as db
from config import ADMIN_BOT_TOKEN, STORE_BOT_TOKEN, CATEGORIES, CURRENCY, WEBAPP_URL
from utils import format_price, save_telegram_photo, build_delivery_message, get_totp_code
from premium_emoji import entities_for

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EDITABLE_FIELDS = ["name", "price", "description", "quantity", "delivery_info", "photo", "active", "warranty_days", "published"]
STOCK_CATEGORIES = [c for c in CATEGORIES if c != "Account"]

DEFAULT_RULES = (
    "📜 វិធាន និង Warranty\n\n"
    "🍎 Fruit / 🎮 Gamepass / ទំនិញផ្សេងទៀត (Trade ក្នុងហ្គេម):\n"
    "ការទិញជា Trade ភ្លាមៗក្នុងហ្គេម — ពេលទទួលរួច មិនអាចដូរ ឬសងប្រាក់វិញបានទេ សូមពិនិត្យមុនទទួល។\n\n"
    "📦 Account — Warranty 14ថ្ងៃ (Standard):\n"
    "- បើអ្នកទិញលុប Authenticator App ចោល → Warranty កាត់មកនៅត្រឹម 7ថ្ងៃប៉ុណ្ណោះ\n"
    "- ការសង/ដូរ Account សងតែក្នុងករណី Roblox Support ដកហូត Account មកវិញ (Owner ដើម Revert) ប៉ុណ្ណោះ\n"
    "- បើអ្នកទិញលុប Email សង្គ្រោះ ឬ Code Authenticator App ចោលទាំងអស់ → គ្មាន Warranty ឬសងប្រាក់វិញក្នុងករណីណាមួយឡើយ"
)


def is_admin(update: Update) -> bool:
    return update.effective_user and db.is_admin_id(update.effective_user.id)


def is_owner(update: Update) -> bool:
    from config import OWNER_IDS
    return update.effective_user and update.effective_user.id in OWNER_IDS


async def deny(update: Update):
    if update.callback_query:
        await update.callback_query.answer("អ្នកមិនមែនជា Admin ទេ", show_alert=True)
    else:
        await update.message.reply_text("អ្នកមិនមែនជា Admin ទេ។")


def caption_of(item, item_id=None):
    header = f"🆔 #{item_id}\n" if item_id else ""
    return (f"{header}📦 {item['category']} — {item['name']}\n"
            f"💵 {format_price(item['price'], CURRENCY)}\n📝 {item['description']}\n📊 ស្តុក: {item['quantity']}")


# ---- start / help ----

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    text = ("👋 Uchiro Store — Admin Bot\n\n"
            "📦 Account (មានរូបភាព):\n/additem - បន្ថែម Account ម្តងមួយ\n\n"
            "⚡ Fruit/Gamepass/Evade/Robux/Blade Ball/MM2 (លឿន បន្ថែមច្រើនម្តងតែម្តង):\n"
            "/addstock - ជ្រើសរើសប្រភេទ រួចបន្ថែមច្រើនក្នុងម្តង\n"
            "/addfruit - បន្ថែម Fruit ច្រើនក្នុងម្តង (Shortcut)\n/addgamepass - បន្ថែម Gamepass ច្រើនក្នុងម្តង (Shortcut)\n"
            "/setstock <id> <ចំនួន> - កែស្តុកលឿន\n/setprice <id> <តម្លៃ> - កែតម្លៃលឿន\n\n"
            "🎮 ជួយ Player (ទាក់ទាញអ្នកលេងចូល Bot):\n"
            "/setcodes - Update Redeem Code ថ្មី\n/settierlist - Update Fruit Tier List\n"
            "/addguide - បន្ថែម Video Guide\n/removeguide <id> - លុប Guide\n/guides - មើល Guide ទាំងអស់\n\n"
            "📜 វិធាន:\n/setrules - កែវិធាន/Warranty\n\n"
            "🏷️ Coupon:\n/addcoupon <code> <percent|fixed> <amount> <max_uses>\n"
            "/listcoupons - មើល Coupon ទាំងអស់\n/disablecoupon <code> - បិទ Coupon\n\n"
            "📤 Draft/Release (ទំនិញថ្មីមិនបង្ហាញភ្លាមទេ):\n"
            "/drafts - មើលទំនិញកំពុងជា Draft\n/release - Publish ទាំងអស់ម្តងតែម្តង\n\n"
            "🛠 គ្រប់គ្រង:\n/listitems - មើល/កែ/លុប ទំនិញ\n/orders - Order កំពុងរង់ចាំ\n/orderhistory - Order ថ្មីៗទាំងអស់\n"
            "/setpayment - កំណត់ QR + ព័ត៌មានទូទាត់\n/showpayment - មើល QR បច្ចុប្បន្ន\n"
            "/setkhqr - កំណត់ KHQR ស្វ័យប្រវត្តិ\n/showkhqr - សាកល្បង KHQR\n"
            "/panel - 🛠 បើក Admin Panel (Web, ងាយប្រើជាង)\n/findemoji - ✨ រក Premium Emoji ID\n"
            "/stats - ស្ថិតិហាង\n/users - អ្នកប្រើប្រាស់ចុងក្រោយ")
    if is_owner(update):
        text += "\n\n👑 Owner:\n/addseller <id> - បន្ថែម Admin\n/removeseller <id> - លុប Admin\n/sellers - មើលបញ្ជី Admin"
    await update.message.reply_text(text)


# ---- web admin panel launcher ----

async def panel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    if not WEBAPP_URL:
        return await update.message.reply_text("Web Panel មិនទាន់បើកដំណើរការទេ (WEBAPP_URL មិនទាន់កំណត់)។")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛠 បើក Admin Panel", web_app=WebAppInfo(url=f"{WEBAPP_URL}/admin"))]])
    await update.message.reply_text("ចុចប៊ូតុងខាងក្រោមដើម្បីបើក Admin Panel (បន្ថែម/កែ/លុប ទំនិញ, មើល Order):", reply_markup=kb)


# ---- premium emoji ID finder ----

async def findemoji(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    context.user_data.clear()
    context.user_data["state"] = "await_emoji_probe"
    await update.message.reply_text(
        "✨ បិទភ្ជាប់ (Paste) Premium Emoji ដែលអ្នកចង់ប្រើ ផ្ញើមកទីនេះ\n"
        "(ត្រូវ Paste ជា Emoji ផ្ទាល់ មិនមែន copy ជា text ធម្មតា — ត្រូវការ Telegram Premium ដើម្បី Paste)"
    )


# ---- rules / warranty ----

async def setrules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    context.user_data.clear()
    context.user_data["state"] = "await_rules"
    await update.message.reply_text(
        "📜 វាយវិធាន/Warranty ថ្មី (វាយបែបណាក៏បាន) — Player នឹងមើលបានតាម /rules:\n\n"
        f"គំរូបច្ចុប្បន្ន:\n{db.get_setting('rules_text', DEFAULT_RULES)}"
    )


# ---- codes / tierlist / guides (admin side) ----

async def setcodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    context.user_data.clear()
    context.user_data["state"] = "await_codes"
    await update.message.reply_text("🎁 វាយ Code ថ្មីទាំងអស់ (១បន្ទាត់ = ១ Code):")


async def settierlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    context.user_data.clear()
    context.user_data["state"] = "await_tierlist"
    await update.message.reply_text("🍈 វាយ Fruit Tier List ថ្មី (វាយបែបណាក៏បាន):")


async def addguide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    text = " ".join(context.args)
    if "|" not in text:
        return await update.message.reply_text("ប្រើ: /addguide ចំណងជើង | Link YouTube\nឧ. /addguide របៀបយក Dough V4 | https://youtu.be/xxxx")
    title, url = [p.strip() for p in text.split("|", 1)]
    guide_id = db.add_guide(title, url)
    await update.message.reply_text(f"✅ បានបន្ថែម Guide #{guide_id}: {title}")


async def removeguide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    if not context.args or not context.args[0].isdigit():
        return await update.message.reply_text("ប្រើ: /removeguide <guide_id>")
    db.delete_guide(int(context.args[0]))
    await update.message.reply_text("✅ បានលុប Guide")


async def guides_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    guides = db.list_guides()
    if not guides:
        return await update.message.reply_text("មិនទាន់មាន Guide ទេ។ ប្រើ /addguide")
    lines = [f"#{g['id']} {g['title']} — {g['video_url']}" for g in guides]
    await update.message.reply_text("📺 Guide ទាំងអស់:\n\n" + "\n".join(lines))


# ---- add item (Account, with photo) ----

async def additem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    context.user_data.clear()
    context.user_data["new_item"] = {}
    kb = [[InlineKeyboardButton(c, callback_data=f"newcat_{c}")] for c in CATEGORIES]
    await update.message.reply_text("ជ្រើសរើសប្រភេទ:", reply_markup=InlineKeyboardMarkup(kb))


async def newcat_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(update):
        return await deny(update)
    await query.answer()
    context.user_data["new_item"] = {"category": query.data.split("_", 1)[1]}
    context.user_data["state"] = "add_name"
    await query.edit_message_text(f"ប្រភេទ: {context.user_data['new_item']['category']}\n\nវាយឈ្មោះទំនិញ:")


ADD_STEPS = {
    "add_name": ("name", str, "តម្លៃប៉ុន្មាន? (លេខ)", "add_price"),
    "add_price": ("price", float, "ពិពណ៌នាលម្អិត:", "add_desc"),
    "add_desc": ("description", str, "ស្តុកប៉ុន្មាន? (លេខគត់)", "add_qty"),
    "add_qty": ("quantity", int, "ព័ត៌មានប្រគល់ជូន (Login/Password/Code) — វាយ - បើមិនទាន់មាន:", "add_delivery"),
    "add_delivery": ("delivery_info", str,
                      "🔐 Authenticator Secret Key (2FA setup key ពី Roblox/គណនី) — វាយ - បើគណនីនេះមិនប្រើ 2FA:",
                      "add_totp"),
    "add_totp": ("totp_secret", str, "ផ្ញើរូបភាពទំនិញ:", "add_photo"),
}


# ---- bulk add (Fruit/Gamepass/Evade/Robux/Blade Ball/MM2) ----

async def addstock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    context.user_data.clear()
    kb = [[InlineKeyboardButton(c, callback_data=f"bulkcat_{c}")] for c in STOCK_CATEGORIES]
    await update.message.reply_text("ជ្រើសរើសប្រភេទ ដែលចង់បន្ថែម Stock ច្រើនក្នុងម្តង:", reply_markup=InlineKeyboardMarkup(kb))


async def bulkcat_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(update):
        return await deny(update)
    await query.answer()
    category = query.data.split("_", 1)[1]
    context.user_data.clear()
    context.user_data["state"] = "bulk_add"
    context.user_data["bulk_category"] = category
    await query.edit_message_text(
        f"⚡ វាយបញ្ជី {category} (១បន្ទាត់ = ១មុខ) ទម្រង់៖\n"
        "ឈ្មោះ, តម្លៃ, ស្តុក\n\n"
        "ឧទាហរណ៍ (វាយច្រើនបន្ទាត់ម្តងបាន):\n"
        "East Dragon, 1.25, 3\n"
        "Buddha, 1.25, 1\n\n"
        "ផ្ញើមកតែម្តង Bot នឹងបន្ថែមទាំងអស់ភ្លាមៗ។ /cancel ដើម្បីបោះបង់"
    )


async def addfruit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    context.user_data.clear()
    context.user_data["state"] = "bulk_add"
    context.user_data["bulk_category"] = "Fruit"
    await update.message.reply_text(
        "🍎 វាយបញ្ជីផ្លែឈើ (១បន្ទាត់ = ១មុខ) ទម្រង់៖\n"
        "ឈ្មោះ, តម្លៃ, ស្តុក\n\n"
        "ឧទាហរណ៍ (វាយច្រើនបន្ទាត់ម្តងបាន):\n"
        "East Dragon, 1.25, 3\n"
        "Buddha, 1.25, 1\n"
        "Rocket, 1, 5\n\n"
        "ផ្ញើមកតែម្តង Bot នឹងបន្ថែមទាំងអស់ភ្លាមៗ។ /cancel ដើម្បីបោះបង់"
    )


async def addgamepass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    context.user_data.clear()
    context.user_data["state"] = "bulk_add"
    context.user_data["bulk_category"] = "Gamepass"
    await update.message.reply_text(
        "🎮 វាយបញ្ជី Gamepass (១បន្ទាត់ = ១មុខ) ទម្រង់៖\n"
        "ឈ្មោះ, តម្លៃ, ស្តុក\n\n"
        "ឧទាហរណ៍ (វាយច្រើនបន្ទាត់ម្តងបាន):\n"
        "2x Boost, 2, 10\n"
        "Fruit Notifier, 1.5, 10\n\n"
        "ផ្ញើមកតែម្តង Bot នឹងបន្ថែមទាំងអស់ភ្លាមៗ។ /cancel ដើម្បីបោះបង់"
    )


async def cancel_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    context.user_data.clear()
    await update.message.reply_text("បានបោះបង់។")


async def setstock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    if len(context.args) != 2 or not context.args[0].isdigit():
        return await update.message.reply_text("ប្រើ: /setstock <item_id> <ចំនួន>")
    item_id = int(context.args[0])
    if not db.get_item(item_id):
        return await update.message.reply_text(f"រកមិនឃើញទំនិញ #{item_id} ទេ")
    try:
        qty = int(context.args[1])
    except ValueError:
        return await update.message.reply_text("ស្តុកត្រូវជាលេខគត់")
    db.update_item_field(item_id, "quantity", qty)
    db.update_item_field(item_id, "active", 1 if qty > 0 else 0)
    await update.message.reply_text(f"✅ បានកែស្តុក #{item_id} ទៅ {qty}")


async def setprice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    if len(context.args) != 2 or not context.args[0].isdigit():
        return await update.message.reply_text("ប្រើ: /setprice <item_id> <តម្លៃ>")
    item_id = int(context.args[0])
    if not db.get_item(item_id):
        return await update.message.reply_text(f"រកមិនឃើញទំនិញ #{item_id} ទេ")
    try:
        price = float(context.args[1])
    except ValueError:
        return await update.message.reply_text("តម្លៃត្រូវជាលេខ")
    db.update_item_field(item_id, "price", price)
    await update.message.reply_text(f"✅ បានកែតម្លៃ #{item_id} ទៅ {format_price(price, CURRENCY)}")


# ---- text / photo state machine ----

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    if not state or not is_admin(update):
        return
    text = update.message.text.strip()

    if state == "await_emoji_probe":
        context.user_data["state"] = None
        entities = update.message.entities or []
        found = [e for e in entities if e.type == "custom_emoji"]
        if not found:
            return await update.message.reply_text(
                "❌ មិនឃើញ Premium Emoji ទេ។ ត្រូវប្រាកដថា៖\n"
                "1) អ្នកមាន Telegram Premium\n"
                "2) Paste Emoji ចូលផ្ទាល់ (មិនមែនវាយ ឬ copy ជា Unicode text ធម្មតា)"
            )
        lines = [f"{text[e.offset:e.offset + e.length]} → `{e.custom_emoji_id}`" for e in found]
        return await update.message.reply_text(
            "✅ រកឃើញ Emoji ID:\n\n" + "\n".join(lines) +
            "\n\nចម្លង ID នេះទុក ផ្ញើមកខ្ញុំ ដើម្បីបញ្ចូលទៅក្នុងសារ Bot ជាកន្លែងណាមួយ។",
            parse_mode="Markdown"
        )

    if state in ADD_STEPS:
        field, cast, next_prompt, next_state = ADD_STEPS[state]
        try:
            value = "" if (field in ("delivery_info", "totp_secret") and text == "-") else cast(text)
        except ValueError:
            return await update.message.reply_text("សូមវាយឲ្យត្រឹមត្រូវ (លេខ) ម្តងទៀត:")
        context.user_data["new_item"][field] = value
        context.user_data["state"] = next_state
        return await update.message.reply_text(next_prompt)

    if state == "edit_value":
        return await apply_edit(update, context, text)

    if state == "await_payment_note":
        db.set_setting("payment_note", "" if text == "-" else text)
        context.user_data["state"] = None
        return await update.message.reply_text("✅ បានកំណត់ព័ត៌មានទូទាត់ (QR + Note) រួចរាល់។")

    if state == "await_codes":
        db.set_setting("codes_text", text)
        context.user_data["state"] = None
        return await update.message.reply_text("✅ បាន Update Code រួចរាល់! Player អាចមើលបានតាម /codes")

    if state == "await_tierlist":
        db.set_setting("tierlist_text", text)
        context.user_data["state"] = None
        return await update.message.reply_text("✅ បាន Update Tier List រួចរាល់! Player អាចមើលបានតាម /tierlist")

    if state == "await_rules":
        db.set_setting("rules_text", text)
        context.user_data["state"] = None
        return await update.message.reply_text("✅ បាន Update វិធាន/Warranty រួចរាល់! Player អាចមើលបានតាម /rules")

    if state == "bulk_add":
        category = context.user_data.get("bulk_category", "Fruit")
        added, errors = [], []
        for i, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 2:
                errors.append(f"បន្ទាត់ {i}: '{line}' — ខ្វះ Comma (ត្រូវការ ឈ្មោះ, តម្លៃ, ស្តុក)")
                continue
            name = parts[0]
            try:
                price = float(parts[1])
                qty = int(parts[2]) if len(parts) > 2 and parts[2] else 1
            except ValueError:
                errors.append(f"បន្ទាត់ {i}: '{line}' — តម្លៃ/ស្តុកមិនមែនជាលេខ")
                continue
            item_id = db.add_item(category, name, price, "", None, "", qty)
            added.append(f"#{item_id} {name}")
        context.user_data.clear()
        reply = f"✅ បានបន្ថែម {len(added)} មុខ ចូល {category}:\n" + "\n".join(added) if added else "គ្មានទំនិញត្រូវបានបន្ថែមទេ។"
        if errors:
            reply += "\n\n⚠️ បញ្ហា:\n" + "\n".join(errors)
        return await update.message.reply_text(reply)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")
    if not state or not is_admin(update):
        return
    file_id = update.message.photo[-1].file_id

    if state == "add_photo":
        path = await save_telegram_photo(context.bot, file_id, "items")
        item = context.user_data["new_item"]
        item["photo_path"] = path
        context.user_data["state"] = None
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ រក្សាទុក", callback_data="save_item"),
                                     InlineKeyboardButton("❌ បោះបង់", callback_data="cancel_item")]])
        with open(path, "rb") as f:
            return await update.message.reply_photo(f, caption=caption_of(item), reply_markup=kb)

    if state == "edit_value" and context.user_data.get("edit_field") == "photo":
        path = await save_telegram_photo(context.bot, file_id, "items")
        return await apply_edit(update, context, path)

    if state == "await_qr":
        path = await save_telegram_photo(context.bot, file_id, "settings")
        db.set_setting("qr_photo_path", path)
        context.user_data["state"] = "await_payment_note"
        return await update.message.reply_text(
            "✅ បាន Save QR។ សូមវាយព័ត៌មានទូទាត់ (ឧ. ABA: 000 111 222 - NAME) — វាយ - បើមិនចង់ដាក់:"
        )


async def save_item_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(update):
        return await deny(update)
    await query.answer()
    if query.data == "cancel_item":
        context.user_data.clear()
        return await query.edit_message_caption("បានបោះបង់។")
    item = context.user_data.get("new_item", {})
    warranty_days = 14 if item["category"] == "Account" else 0
    item_id = db.add_item(item["category"], item["name"], item["price"], item["description"],
                           item["photo_path"], item.get("delivery_info", ""), item["quantity"], warranty_days)
    if item.get("totp_secret"):
        db.update_item_field(item_id, "totp_secret", item["totp_secret"])
    context.user_data.clear()
    await query.edit_message_caption(f"✅ រក្សាទុករួច! (ID #{item_id})" + (" — 🛡️ Warranty 14ថ្ងៃស្វ័យប្រវត្តិ" if warranty_days else ""))


# ---- list / edit / delete ----

async def listitems(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    items = db.get_all_items()
    if not items:
        return await update.message.reply_text("មិនទាន់មានទំនិញ។ ប្រើ /additem")
    for it in items:
        status = "🟢" if it["active"] and it["quantity"] > 0 else "🔴"
        draft_tag = " 📝Draft" if not it["published"] else ""
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✏️ កែប្រែ", callback_data=f"edit_{it['id']}"),
                                     InlineKeyboardButton("🗑 លុប", callback_data=f"del_{it['id']}")]])
        caption = f"{status}{draft_tag} {caption_of(it, it['id'])}"
        if it["photo_file_id"] and os.path.exists(it["photo_file_id"]):
            with open(it["photo_file_id"], "rb") as f:
                await update.message.reply_photo(f, caption=caption, reply_markup=kb)
        else:
            await update.message.reply_text(caption, reply_markup=kb)


async def delete_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(update):
        return await deny(update)
    await query.answer()
    item_id = int(query.data.split("_")[1])
    db.delete_item(item_id)
    await query.message.reply_text(f"🗑 បានលុប #{item_id}")


async def edit_start_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(update):
        return await deny(update)
    await query.answer()
    item_id = int(query.data.split("_")[1])
    context.user_data["edit_item_id"] = item_id
    kb = [[InlineKeyboardButton(f, callback_data=f"field_{f}")] for f in EDITABLE_FIELDS]
    await query.message.reply_text("កែផ្នែកណា?", reply_markup=InlineKeyboardMarkup(kb))


async def edit_field_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(update):
        return await deny(update)
    await query.answer()
    field = query.data.split("_", 1)[1]
    context.user_data["edit_field"] = field
    context.user_data["state"] = "edit_value"
    prompt = "ផ្ញើរូបភាពថ្មី:" if field == "photo" else \
        ("វាយ 1 ដើម្បីបើក ឬ 0 ដើម្បីបិទ:" if field == "active" else f"វាយតម្លៃថ្មីសម្រាប់ {field}:")
    await query.message.reply_text(prompt)


async def apply_edit(update: Update, context: ContextTypes.DEFAULT_TYPE, raw_value):
    item_id = context.user_data.get("edit_item_id")
    field = context.user_data.get("edit_field")
    if item_id is None or field is None:
        return
    db_field = "photo_file_id" if field == "photo" else field
    value = raw_value
    try:
        if field == "price":
            value = float(raw_value)
        elif field in ("quantity", "active", "warranty_days", "published"):
            value = int(raw_value)
    except ValueError:
        return await update.message.reply_text("សូមវាយជាលេខ:")
    db.update_item_field(item_id, db_field, value)
    context.user_data["state"] = None
    context.user_data.pop("edit_item_id", None)
    context.user_data.pop("edit_field", None)
    await update.message.reply_text(f"✅ បានកែ {field} របស់ #{item_id}")


# ---- coupons ----

async def addcoupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    args = context.args
    if len(args) != 4 or args[1] not in ("percent", "fixed"):
        return await update.message.reply_text(
            "ប្រើ: /addcoupon <code> <percent|fixed> <amount> <max_uses>\n"
            "ឧ. /addcoupon SAVE20 percent 20 10  (20% off, ប្រើបានអតិបរមា 10ដង, ១ដងក្នុងម្នាក់)\n"
            "ឧ. /addcoupon FLAT5 fixed 5 1  ($5 off, ប្រើបានតែ 1ដងសរុប)"
        )
    try:
        amount = float(args[2])
        max_uses = int(args[3])
    except ValueError:
        return await update.message.reply_text("Amount/Max uses ត្រូវជាលេខ")
    code = db.add_coupon(args[0], args[1], amount, max_uses)
    unit = "%" if args[1] == "percent" else CURRENCY
    await update.message.reply_text(
        f"✅ បាន Save Coupon: {code}\n{amount}{unit} off, អតិបរមា {max_uses}ដងសរុប, 1ដងក្នុងម្នាក់ស្វ័យប្រវត្តិ"
    )


async def listcoupons_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    coupons = db.list_coupons()
    if not coupons:
        return await update.message.reply_text("មិនទាន់មាន Coupon ទេ។ ប្រើ /addcoupon")
    lines = []
    for c in coupons:
        unit = "%" if c["discount_type"] == "percent" else CURRENCY
        status = "🟢" if c["active"] else "🔴"
        lines.append(f"{status} {c['code']} — {c['amount']}{unit} off ({c['used_count']}/{c['max_uses']} ប្រើ)")
    await update.message.reply_text("🏷️ Coupon ទាំងអស់:\n\n" + "\n".join(lines))


async def disablecoupon_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    if not context.args:
        return await update.message.reply_text("ប្រើ: /disablecoupon <code>")
    db.disable_coupon(context.args[0])
    await update.message.reply_text(f"✅ បានបិទ Coupon {context.args[0].upper()}")


# ---- draft / release ----

async def release_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    drafts = db.get_draft_items()
    if not drafts:
        return await update.message.reply_text("គ្មានទំនិញថ្មីរង់ចាំ Release ទេ (ទំនិញទាំងអស់ Publish រួចហើយ)។")
    released = db.release_all_drafts()
    lines = [f"#{it['id']} {it['name']} ({it['category']})" for it in released]
    await update.message.reply_text(f"🚀 បាន Publish {len(released)} មុខភ្លាមៗ:\n\n" + "\n".join(lines))


async def drafts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    drafts = db.get_draft_items()
    if not drafts:
        return await update.message.reply_text("គ្មានទំនិញនៅជា Draft ទេ។")
    lines = [f"#{it['id']} {it['name']} ({it['category']}) — {format_price(it['price'], CURRENCY)}" for it in drafts]
    await update.message.reply_text(
        f"📝 ទំនិញនៅជា Draft ({len(drafts)}) — មិនទាន់មានអតិថិជនឃើញទេ:\n\n" + "\n".join(lines) +
        "\n\nវាយ /release ដើម្បី Publish ទាំងអស់ម្តងតែម្តង"
    )


# ---- spin wheel (free - unlocked after buying an Account) ----

async def addspin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    if len(context.args) < 2:
        return await update.message.reply_text(
            "ប្រើ: /addspin <ឈ្មោះ> <weight>\n"
            "ឧ. /addspin Buddha 80\n/addspin Kitsune 2\n\n"
            "weight មិនចាំបាច់បូកបាន 100 ទេ — ប្រព័ន្ធគណនា % ដោយស្វ័យប្រវត្តិពី weight ធៀបនឹងផលបូកទាំងអស់"
        )
    name = " ".join(context.args[:-1])
    try:
        weight = float(context.args[-1])
    except ValueError:
        return await update.message.reply_text("weight ត្រូវជាលេខ")
    db.add_spin_item(name, weight)
    pool = db.list_spin_items()
    total = sum(p["weight"] for p in pool)
    pct = weight / total * 100 if total else 0
    await update.message.reply_text(f"✅ បានបន្ថែម {name} ចូល Spin Pool (≈{pct:.1f}%)")


async def listspins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    pool = db.list_spin_items()
    if not pool:
        return await update.message.reply_text("Spin Pool ទទេ។ ប្រើ /addspin")
    total = sum(p["weight"] for p in pool)
    lines = [f"#{p['id']} {p['name']} — {p['weight']/total*100:.1f}%" for p in pool]
    await update.message.reply_text("🎡 Spin Pool ($0 ឥតគិតថ្លៃ, Unlock ក្រោយទិញ Account):\n\n" + "\n".join(lines))


async def removespin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    if not context.args or not context.args[0].isdigit():
        return await update.message.reply_text("ប្រើ: /removespin <id>")
    db.remove_spin_item(int(context.args[0]))
    await update.message.reply_text("✅ បានលុប")


async def spinclaims_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    pending = db.get_pending_spin_wins()
    if not pending:
        return await update.message.reply_text("គ្មាន Spin Win កំពុងរង់ចាំប្រគល់ជូនទេ។")
    for w in pending:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ ប្រគល់ជូនរួច", callback_data=f"spindeliver_{w['id']}")]])
        await update.message.reply_text(
            f"🎉 Win #{w['id']}\n👤 @{w['username'] or 'N/A'} (id: {w['chat_id']})\n"
            f"🎁 {w['reward_name']}\n🕐 {w['created_at']}", reply_markup=kb
        )


async def spindeliver_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(update):
        return await deny(update)
    await query.answer()
    win_id = int(query.data.split("_")[1])
    db.mark_spin_delivered(win_id)
    await query.edit_message_text(query.message.text + "\n\n✅ ប្រគល់ជូនរួច")


# ---- orders ----

async def orderhistory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    orders = db.get_recent_orders(20)
    if not orders:
        return await update.message.reply_text("មិនទាន់មាន Order ណាទេ។")
    icon = {"pending": "⏳", "approved": "✅", "rejected": "❌"}
    lines = []
    for o in orders:
        lines.append(f"{icon.get(o['status'], '•')} #{o['id']} {o['item_name']} — @{o['buyer_username'] or 'N/A'} ({o['created_at']})")
    await update.message.reply_text("🧾 Order ថ្មីៗ (20):\n\n" + "\n".join(lines))


async def orders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    pending = db.get_orders_by_status("pending")
    if not pending:
        return await update.message.reply_text("មិនមាន Order កំពុងរង់ចាំ។")
    for order in pending:
        item = db.get_item(order["item_id"])
        caption = (f"🧾 Order #{order['id']}\n👤 @{order['buyer_username'] or 'N/A'} ({order['buyer_chat_id']})\n"
                   f"📦 {item['name'] if item else 'N/A'}\n💵 {format_price(item['price'], CURRENCY) if item else '?'}")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ អនុម័ត", callback_data=f"appr_{order['id']}"),
                                     InlineKeyboardButton("❌ បដិសេធ", callback_data=f"rej_{order['id']}")]])
        if order["payment_photo_file_id"] and os.path.exists(order["payment_photo_file_id"]):
            with open(order["payment_photo_file_id"], "rb") as f:
                await update.message.reply_photo(f, caption=caption, reply_markup=kb)
        else:
            await update.message.reply_text(caption, reply_markup=kb)


async def order_decision_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(update):
        return await deny(update)
    await query.answer()
    action, order_id = query.data.split("_")
    order_id = int(order_id)
    order = db.get_order(order_id)
    if not order or order["status"] != "pending":
        return await query.message.reply_text("Order នេះដោះស្រាយរួចហើយ។")

    item = db.get_item(order["item_id"])
    store_bot = Bot(token=STORE_BOT_TOKEN)

    if action == "appr":
        db.set_order_approved(order_id)
        db.decrement_stock(order["item_id"])
        msg = f"🎉 ការទូទាត់សម្រាប់ {item['name']} ត្រូវបានអនុម័ត! អរគុណដែលទិញនៅ Uchiro Store 🇰🇭"
        msg += "\n\n" + build_delivery_message(item)
        if item["category"] == "Account":
            db.grant_spin_credit(order["buyer_chat_id"], 1)
            msg += "\n\n🎡 អ្នកទទួលបាន Spin ឥតគិតថ្លៃ 1 ដង! វាយ /spin ដើម្បីលេង"
        try:
            await store_bot.send_message(order["buyer_chat_id"], msg, parse_mode="Markdown")
        except Exception:
            await store_bot.send_message(order["buyer_chat_id"], msg)  # fallback if item name breaks Markdown
        await query.message.reply_text(f"✅ អនុម័ត #{order_id}")
    else:
        db.update_order_status(order_id, "rejected")
        await store_bot.send_message(order["buyer_chat_id"],
                                      f"❌ ការទូទាត់សម្រាប់ {item['name'] if item else ''} មិនត្រូវបានអនុម័តទេ។ សូមទាក់ទងម្ចាស់ហាង។")
        await query.message.reply_text(f"❌ បដិសេធ #{order_id}")


# ---- payment QR ----

async def setpayment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    context.user_data["state"] = "await_qr"
    await update.message.reply_text("សូមផ្ញើរូបភាព QR Code សម្រាប់ទូទាត់:")


async def setkhqr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    text = " ".join(context.args)
    parts = [p.strip() for p in text.split("|")]
    if len(parts) < 1 or not parts[0]:
        return await update.message.reply_text(
            "ប្រើ: /setkhqr account_id | ឈ្មោះហាង | ក្រុង\n"
            "ឧ. /setkhqr sovan_noreakyout@wing | Uchiro Store | Phnom Penh\n\n"
            "account_id យកពី App ធនាគាររបស់អ្នក (ផ្នែក KHQR/My QR)"
        )
    db.set_setting("khqr_account_id", parts[0])
    db.set_setting("khqr_merchant_name", parts[1] if len(parts) > 1 and parts[1] else "Uchiro Store")
    db.set_setting("khqr_merchant_city", parts[2] if len(parts) > 2 and parts[2] else "Phnom Penh")
    await update.message.reply_text(
        f"✅ បាន Save KHQR!\naccount_id: {parts[0]}\n\n"
        "ចាប់ពីពេលនេះទៅ រាល់ការទិញនឹងបង្ហាញ QR ជាមួយតម្លៃពិតដោយស្វ័យប្រវត្តិ។ សាកល្បងចុច 'ទិញឥឡូវ' លើ Store Bot ដើម្បីផ្ទៀងផ្ទាត់។"
    )


async def showkhqr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    account_id = db.get_setting("khqr_account_id")
    if not account_id:
        return await update.message.reply_text("មិនទាន់កំណត់ KHQR ទេ។ ប្រើ /setkhqr")
    from utils import generate_khqr_image
    path = generate_khqr_image(account_id, db.get_setting("khqr_merchant_name", "Uchiro Store"),
                                db.get_setting("khqr_merchant_city", "Phnom Penh"), 1.00, "TEST")
    if not path:
        return await update.message.reply_text(
            "⚠️ មិនអាចបង្កើត KHQR បានទេ (library មិនទាន់ដំឡើង ឬ account_id មិនត្រឹមត្រូវ)។ "
            "Bot នឹងប្រើ QR ស្តាទិចធម្មតា (/setpayment) ជំនួសវិញដោយស្វ័យប្រវត្តិ។"
        )
    with open(path, "rb") as f:
        await update.message.reply_photo(f, caption=f"KHQR សាកល្បង ($1.00)\naccount_id: {account_id}")


async def showpayment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    qr = db.get_setting("qr_photo_path")
    note = db.get_setting("payment_note", "")
    if not qr or not os.path.exists(qr):
        return await update.message.reply_text("មិនទាន់កំណត់ QR ទេ។ ប្រើ /setpayment")
    with open(qr, "rb") as f:
        await update.message.reply_photo(f, caption=note or "QR ទូទាត់បច្ចុប្បន្ន")


# ---- stats ----

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    total_users = db.count_users()
    total_items = len(db.get_all_items())
    orders = db.count_orders_by_status()
    text = (
        "📊 ស្ថិតិហាង\n\n"
        f"👥 អ្នកប្រើប្រាស់សរុប (ធ្លាប់ចូល Store Bot): {total_users}\n"
        f"📦 ទំនិញសរុបក្នុងស្តុក: {total_items}\n\n"
        f"🧾 Order កំពុងរង់ចាំ: {orders.get('pending', 0)}\n"
        f"✅ Order អនុម័តរួច: {orders.get('approved', 0)}\n"
        f"❌ Order បដិសេធ: {orders.get('rejected', 0)}"
    )
    await update.message.reply_text(text, entities=entities_for(text))


async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    users = db.list_users(30)
    if not users:
        return await update.message.reply_text("មិនទាន់មានអ្នកប្រើប្រាស់ទេ។")
    lines = [f"@{u['username'] or 'N/A'} (id: {u['chat_id']}) — ចុងក្រោយ {u['last_seen']}" for u in users]
    await update.message.reply_text(f"👥 អ្នកប្រើប្រាស់ចុងក្រោយ ({db.count_users()} សរុប):\n\n" + "\n".join(lines))


# ---- seller management (owner only) ----

async def addseller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return await deny(update)
    if not context.args or not context.args[0].isdigit():
        return await update.message.reply_text("ប្រើ: /addseller <chat_id>")
    chat_id = int(context.args[0])
    db.add_seller(chat_id)
    await update.message.reply_text(f"✅ បានបន្ថែម Admin: {chat_id}")


async def removeseller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return await deny(update)
    if not context.args or not context.args[0].isdigit():
        return await update.message.reply_text("ប្រើ: /removeseller <chat_id>")
    chat_id = int(context.args[0])
    db.remove_seller(chat_id)
    await update.message.reply_text(f"✅ បានលុប Admin: {chat_id}")


async def sellers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    from config import OWNER_IDS
    lines = [f"👑 Owner: {oid}" for oid in OWNER_IDS]
    lines += [f"🧑‍💼 Admin: {s['chat_id']}" for s in db.list_sellers()]
    await update.message.reply_text("\n".join(lines) or "មិនមាន Admin ណាទេ។")


# ---- error handler ----

async def on_error(update, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Admin bot error", exc_info=context.error)
    try:
        if isinstance(update, Update) and update.effective_chat:
            await context.bot.send_message(update.effective_chat.id, "⚠️ មានបញ្ហាបច្ចេកទេស សូមព្យាយាមម្តងទៀត។")
    except Exception:
        pass


# ---- build ----

def build_app():
    app = Application.builder().token(ADMIN_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("additem", additem))
    app.add_handler(CommandHandler("addstock", addstock))
    app.add_handler(CommandHandler("addfruit", addfruit))
    app.add_handler(CommandHandler("addgamepass", addgamepass))
    app.add_handler(CommandHandler("setstock", setstock))
    app.add_handler(CommandHandler("setprice", setprice))
    app.add_handler(CommandHandler("cancel", cancel_state))
    app.add_handler(CommandHandler("setcodes", setcodes))
    app.add_handler(CommandHandler("settierlist", settierlist))
    app.add_handler(CommandHandler("setrules", setrules))
    app.add_handler(CommandHandler("findemoji", findemoji))
    app.add_handler(CommandHandler("panel", panel_cmd))
    app.add_handler(CommandHandler("addcoupon", addcoupon))
    app.add_handler(CommandHandler("listcoupons", listcoupons_cmd))
    app.add_handler(CommandHandler("disablecoupon", disablecoupon_cmd))
    app.add_handler(CommandHandler("release", release_cmd))
    app.add_handler(CommandHandler("addspin", addspin))
    app.add_handler(CommandHandler("listspins", listspins_cmd))
    app.add_handler(CommandHandler("removespin", removespin))
    app.add_handler(CommandHandler("spinclaims", spinclaims_cmd))
    app.add_handler(CommandHandler("drafts", drafts_cmd))
    app.add_handler(CommandHandler("addguide", addguide))
    app.add_handler(CommandHandler("removeguide", removeguide))
    app.add_handler(CommandHandler("guides", guides_cmd))
    app.add_handler(CommandHandler("listitems", listitems))
    app.add_handler(CommandHandler("orders", orders_cmd))
    app.add_handler(CommandHandler("orderhistory", orderhistory_cmd))
    app.add_handler(CommandHandler("addseller", addseller))
    app.add_handler(CommandHandler("removeseller", removeseller))
    app.add_handler(CommandHandler("sellers", sellers_cmd))
    app.add_handler(CommandHandler("setpayment", setpayment))
    app.add_handler(CommandHandler("setkhqr", setkhqr))
    app.add_handler(CommandHandler("showkhqr", showkhqr))
    app.add_handler(CommandHandler("showpayment", showpayment))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("users", users_cmd))

    app.add_handler(CallbackQueryHandler(newcat_cb, pattern=r"^newcat_"))
    app.add_handler(CallbackQueryHandler(bulkcat_cb, pattern=r"^bulkcat_"))
    app.add_handler(CallbackQueryHandler(save_item_cb, pattern=r"^(save_item|cancel_item)$"))
    app.add_handler(CallbackQueryHandler(edit_start_cb, pattern=r"^edit_\d+$"))
    app.add_handler(CallbackQueryHandler(edit_field_cb, pattern=r"^field_"))
    app.add_handler(CallbackQueryHandler(delete_cb, pattern=r"^del_\d+$"))
    app.add_handler(CallbackQueryHandler(order_decision_cb, pattern=r"^(appr|rej)_\d+$"))
    app.add_handler(CallbackQueryHandler(spindeliver_cb, pattern=r"^spindeliver_\d+$"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_error_handler(on_error)
    return app


if __name__ == "__main__":
    db.init_db()
    build_app().run_polling()
