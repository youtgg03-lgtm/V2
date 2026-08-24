"""
store_bot.py — Uchiro Store (customer-facing bot)
Kept deliberately minimal — browsing, checkout, and order history all
live in the Mini App now. This bot's job is just to welcome people in
and hand them the app, plus a couple of quick text fallbacks.
"""

import logging
from telegram import Update, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes

import database as db
from config import STORE_BOT_TOKEN, WEBAPP_URL, ADMIN_USERNAME, CHANNEL_USERNAME, STORE_NAME

logging.basicConfig(level=logging.INFO)


def _open_app_keyboard():
    if not WEBAPP_URL:
        return None
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🛍️ បើក Uchiro Store", web_app=WebAppInfo(url=WEBAPP_URL))
    ]])


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.touch_user(user.id, user.username)
    text = (
        f'<tg-emoji emoji-id="5413694143601842851">👋</tg-emoji> សូមស្វាគមន៍មកកាន់ {STORE_NAME}!\n\n'
        '<tg-emoji emoji-id="5836672976862319297">🛍️</tg-emoji> Blox Fruits Account · MM2 · Blade Ball · Gamepass — ទូទាត់ KHQR ប្រគល់ជូនស្វ័យប្រវត្តិ។\n\n'
        'ចុចប៊ូតុងខាងក្រោមដើម្បីមើលទំនិញ ទិញ និងមើល Order History ទាំងអស់នៅកន្លែងតែមួយ <tg-emoji emoji-id="5470177992950946662">👇</tg-emoji>\n\n'
        '📋 <b>ឬវាយ Command ទាំងនេះផ្ទាល់:</b>\n'
        '/shop — <tg-emoji emoji-id="5836672976862319297">🛍️</tg-emoji> មើលទំនិញ\n'
        '/myorders — <tg-emoji emoji-id="5264959791213586839">🧾</tg-emoji> មើល Order History\n'
        '/howtobuy — <tg-emoji emoji-id="5312361253610475399">🛒</tg-emoji> របៀបទិញ\n'
        '/howtologin — <tg-emoji emoji-id="6109136102868652214">🔐</tg-emoji> របៀបចូលគណនី\n'
        '/help — <tg-emoji emoji-id="6106980145250177382">💬</tg-emoji> ជំនួយ + ទាក់ទង Admin'
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=_open_app_keyboard())


async def myorders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    orders = db.get_orders_by_buyer(update.effective_user.id)
    if not orders:
        return await update.message.reply_text(
            '<tg-emoji emoji-id="5352896944496728039">📭</tg-emoji> អ្នកមិនទាន់មាន Order ទេ។ បើក Store ដើម្បីចាប់ផ្តើមទិញ <tg-emoji emoji-id="5470177992950946662">👇</tg-emoji>',
            parse_mode="HTML",
            reply_markup=_open_app_keyboard())
    await update.message.reply_text(
        f'<tg-emoji emoji-id="5264959791213586839">🧾</tg-emoji> អ្នកមាន {len(orders)} Order — មើលលម្អិត (login/password/live code) ក្នុង App <tg-emoji emoji-id="5470177992950946662">👇</tg-emoji>',
        parse_mode="HTML",
        reply_markup=_open_app_keyboard())


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f'<tg-emoji emoji-id="6106980145250177382">💬</tg-emoji> ជំនួយ:\n'
        f'<tg-emoji emoji-id="5258011929993026890">👤</tg-emoji> Admin: @{ADMIN_USERNAME}\n'
        f'<tg-emoji emoji-id="6300742299114541958">📢</tg-emoji> Channel: @{CHANNEL_USERNAME}\n\n'
        "📋 Command ទាំងអស់:\n"
        "/shop — មើលទំនិញ\n"
        "/myorders — Order History\n"
        "/howtobuy — របៀបទិញ\n"
        "/howtologin — របៀបចូលគណនី\n\n"
        "Warranty និង FAQ ពេញលេញមាននៅក្នុងផ្ទាំង Help របស់ App។",
        parse_mode="HTML",
        reply_markup=_open_app_keyboard())


async def howtobuy_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        '<tg-emoji emoji-id="5312361253610475399">🛒</tg-emoji> <b>របៀបទិញ:</b>\n\n'
        '<tg-emoji emoji-id="5382322671679708881">1️⃣</tg-emoji> ចុច \'បើក Uchiro Store\' ខាងក្រោម\n'
        '<tg-emoji emoji-id="5381990043642502553">2️⃣</tg-emoji> ជ្រើសរើសប្រភេទ (Account / MM2 / Fruit / ...)\n'
        '<tg-emoji emoji-id="5381879959335738545">3️⃣</tg-emoji> ចុចលើទំនិញ → ចុច \'ទិញឥឡូវ\'\n'
        '<tg-emoji emoji-id="5382054253403577563">4️⃣</tg-emoji> Scan KHQR ដើម្បីទូទាត់ → Upload Screenshot\n'
        '<tg-emoji emoji-id="5391197405553107640">5️⃣</tg-emoji> រង់ចាំ Admin បញ្ជាក់ (ជាធម្មតាលឿនណាស់) — នៅពេលបញ្ជាក់រួច គណនី/ទំនិញនឹងផ្ញើមកអោយភ្លាមតាម Bot នេះ\n\n'
        '<tg-emoji emoji-id="5298877105000439431">🏷️</tg-emoji> មាន Coupon? វាយក្នុងទំព័រទូទាត់ មុនពេល Scan QR។'
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=_open_app_keyboard())


async def howtologin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        '<tg-emoji emoji-id="6109136102868652214">🔐</tg-emoji> <b>របៀបចូលគណនី (Account ដែលមាន Authenticator):</b>\n\n'
        '<tg-emoji emoji-id="5382322671679708881">1️⃣</tg-emoji> ទាញយក App ឈ្មោះ <b>Google Authenticator</b> ឬ <b>Authy</b> ពី App Store / Play Store\n'
        '<tg-emoji emoji-id="5381990043642502553">2️⃣</tg-emoji> បើក /myorders → ចុច Order → ចុច \'មើលគណនីរបស់ខ្ញុំ\'\n'
        '<tg-emoji emoji-id="5381879959335738545">3️⃣</tg-emoji> Copy Name និង Password → ចូល Roblox ដោយប្រើវា\n'
        '<tg-emoji emoji-id="5382054253403577563">4️⃣</tg-emoji> Roblox នឹងសួរលេខកូដ 6 ខ្ទង់ → ត្រឡប់មក App វិញ → Copy លេខកូដ Live → បិទភ្ជាប់\n'
        '<tg-emoji emoji-id="5391197405553107640">5️⃣</tg-emoji> លេខកូដប្រែរាល់ 30 វិនាទី — ចុច \'Refresh\' បើលេខចាស់ហួសពេល\n\n'
        '<tg-emoji emoji-id="6265015769008969527">⚠️</tg-emoji> កុំលុប Authenticator ចោល — បើលុប Warranty នឹងធ្លាក់ពី 14ថ្ងៃ មក 7ថ្ងៃ។'
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=_open_app_keyboard())


async def _post_init(application: Application):
    from telegram import BotCommand
    await application.bot.set_my_commands([
        BotCommand("start", "🏠 ចាប់ផ្តើម"),
        BotCommand("shop", "🛍️ មើលទំនិញ"),
        BotCommand("myorders", "🧾 Order History"),
        BotCommand("howtobuy", "🛒 របៀបទិញ"),
        BotCommand("howtologin", "🔐 របៀបចូលគណនី"),
        BotCommand("help", "💬 ជំនួយ"),
    ])


def build_app():
    application = Application.builder().token(STORE_BOT_TOKEN).post_init(_post_init).build()
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("shop", start_cmd))
    application.add_handler(CommandHandler("myorders", myorders_cmd))
    application.add_handler(CommandHandler("orderhistory", myorders_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("support", help_cmd))
    application.add_handler(CommandHandler("howtobuy", howtobuy_cmd))
    application.add_handler(CommandHandler("howtologin", howtologin_cmd))
    return application


if __name__ == "__main__":
    db.init_db()
    build_app().run_polling()
