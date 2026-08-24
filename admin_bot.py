"""
admin_bot.py — Uchiro Store (owner-only bot)
Kept minimal on purpose — adding items, approving orders, and viewing
stock all happen in the Admin Mini App panel now. This bot only keeps
the things that are genuinely easier as a chat command: creating
coupons, broadcasting to buyers, and a quick /stats check.
"""

import asyncio
import logging
from telegram import Update, WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

import database as db
import services
from config import ADMIN_BOT_TOKEN, STORE_BOT_TOKEN, WEBAPP_URL

logging.basicConfig(level=logging.INFO)

EMOJI_GREEN = '<tg-emoji emoji-id="6138568461481153914">🟢</tg-emoji>'
EMOJI_RED = '<tg-emoji emoji-id="6170475670443922913">🔴</tg-emoji>'


def _admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not db.is_admin_id(update.effective_user.id):
            return await update.message.reply_text('<tg-emoji emoji-id="5240241223632954241">🚫</tg-emoji> Owner only.', parse_mode="HTML")
        return await func(update, context)
    return wrapper


@_admin_only
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.is_admin_id(update.effective_user.id):
        return await update.message.reply_text('<tg-emoji emoji-id="5240241223632954241">🚫</tg-emoji> Owner only.', parse_mode="HTML")
    text = (
        '<tg-emoji emoji-id="5413694143601842851">👋</tg-emoji> Uchiro Store — Admin Bot\n\n'
        '<tg-emoji emoji-id="5987635334945444280">📋</tg-emoji> <b>Command ទាំងអស់:</b>\n'
        '/panel — <tg-emoji emoji-id="5231200819986047254">📊</tg-emoji> Admin Panel (add product, approve order, coupons)\n'
        '/stats — <tg-emoji emoji-id="6300854578149593766">📈</tg-emoji> ស្ថិតិលឿន\n'
        '/addcoupon — <tg-emoji emoji-id="5298877105000439431">🏷️</tg-emoji> បង្កើត Coupon\n'
        '/listcoupons — <tg-emoji emoji-id="5987635334945444280">📋</tg-emoji> មើល Coupon\n'
        '/disablecoupon — <tg-emoji emoji-id="6170475670443922913">🔴</tg-emoji> បិទ Coupon\n'
        '/broadcast — <tg-emoji emoji-id="6300742299114541958">📢</tg-emoji> ផ្សព្វផ្សាយសារ\n'
        '/help — <tg-emoji emoji-id="6106980145250177382">💬</tg-emoji> ពន្យល់លម្អិត\n\n'
        'ចុចប៊ូតុងខាងក្រោមដើម្បីបើក Panel ភ្លាមៗ <tg-emoji emoji-id="5470177992950946662">👇</tg-emoji>'
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(
        "📊 Open Admin Panel", web_app=WebAppInfo(url=f"{WEBAPP_URL}/admin"))]]) if WEBAPP_URL else None
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)


@_admin_only
async def panel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not WEBAPP_URL:
        return await update.message.reply_text('<tg-emoji emoji-id="6265015769008969527">⚠️</tg-emoji> WEBAPP_URL not set — deploy first, then this button will work.', parse_mode="HTML")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(
        "📊 Open Admin Panel", web_app=WebAppInfo(url=f"{WEBAPP_URL}/admin"))]])
    await update.message.reply_text(
        '<tg-emoji emoji-id="5462921117423384478">🛠️</tg-emoji> Admin Panel — add products, approve orders, manage coupons, all here:',
        parse_mode="HTML",
        reply_markup=kb)


@_admin_only
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_users = db.count_users()
    by_status = db.count_orders_by_status()
    text = (
        f'<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji> <b>Uchiro Store stats</b>\n\n'
        f'<tg-emoji emoji-id="6001526766714227911">👥</tg-emoji> Users: <code>{total_users}</code>\n'
        f'<tg-emoji emoji-id="6289745241511565742">⏳</tg-emoji> Pending orders: <code>{by_status.get("pending", 0)}</code>\n'
        f'<tg-emoji emoji-id="5904704361182798355">✅</tg-emoji> Approved orders: <code>{by_status.get("approved", 0)}</code>\n'
        f'<tg-emoji emoji-id="6300696192640620174">❌</tg-emoji> Rejected: <code>{by_status.get("rejected", 0)}</code>\n'
    )
    await update.message.reply_text(text, parse_mode="HTML")


@_admin_only
async def addcoupon_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 4 or args[1] not in ("percent", "fixed"):
        return await update.message.reply_text(
            "ប្រើ: /addcoupon CODE percent|fixed AMOUNT MAX_USES\n"
            "ឧ. /addcoupon FRUIT20 percent 20 50")
    code, dtype, amount, max_uses = args
    try:
        db.add_coupon(code, dtype, float(amount), int(max_uses))
    except ValueError:
        return await update.message.reply_text("AMOUNT និង MAX_USES ត្រូវជាលេខ។")
    await update.message.reply_text(f'<tg-emoji emoji-id="5904704361182798355">✅</tg-emoji> Coupon {code.upper()} បានបង្កើត — មើល/បិទបានក្នុង Panel ដែរ។', parse_mode="HTML")


@_admin_only
async def listcoupons_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coupons = db.list_coupons()
    if not coupons:
        return await update.message.reply_text("គ្មាន Coupon ទេ។")
    
    lines = []
    for c in coupons:
        status_icon = EMOJI_GREEN if c['active'] else EMOJI_RED
        unit = '%' if c['discount_type'] == 'percent' else '$'
        lines.append(f"{status_icon} <code>{c['code']}</code> — {c['amount']:.0f}{unit} off ({c['used_count']}/{c['max_uses']})")
        
    await update.message.reply_text('<tg-emoji emoji-id="5298877105000439431">🏷️</tg-emoji> <b>Coupons:</b>\n' + "\n".join(lines), parse_mode="HTML")


@_admin_only
async def disablecoupon_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("ប្រើ: /disablecoupon CODE")
    db.disable_coupon(context.args[0])
    await update.message.reply_text(f'<tg-emoji emoji-id="6170475670443922913">🔴</tg-emoji> Coupon {context.args[0].upper()} បិទរួច។', parse_mode="HTML")


@_admin_only
async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = " ".join(context.args) if context.args else None
    if not message_text:
        return await update.message.reply_text(
            'ប្រើ: /broadcast <សារ>\n\nឧ. /broadcast <tg-emoji emoji-id="6107318416874410520">🎉</tg-emoji> មានទំនិញថ្មី! ចូលមើលឥឡូវ', parse_mode="HTML")

    user_ids = db.all_user_ids()
    await update.message.reply_text(f"កំពុងផ្ញើទៅ {len(user_ids)} នាក់…")

    store_bot = Bot(token=STORE_BOT_TOKEN)
    sent, failed = 0, 0
    for i in range(0, len(user_ids), 25):
        for uid in user_ids[i:i + 25]:
            try:
                await store_bot.send_message(uid, f'<tg-emoji emoji-id="6300742299114541958">📢</tg-emoji> {message_text}', parse_mode="HTML")
                sent += 1
            except Exception:
                failed += 1
        await asyncio.sleep(1)
    await update.message.reply_text(f'<tg-emoji emoji-id="5904704361182798355">✅</tg-emoji> ជោគជ័យ: {sent}, បរាជ័យ: {failed}', parse_mode="HTML")


async def order_decision_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not db.is_admin_id(query.from_user.id):
        return await query.answer("Owner only.", show_alert=True)

    action, order_id_str = query.data.split("_", 1)
    order_id = int(order_id_str)

    if action == "appr":
        ok = services.approve_order(order_id)
        result_text = '<tg-emoji emoji-id="5904704361182798355">✅</tg-emoji> អនុម័តរួច — ប្រគល់ជូនរួច' if ok else '<tg-emoji emoji-id="6265015769008969527">⚠️</tg-emoji> Order នេះត្រូវបានដោះស្រាយរួចហើយ'
    else:
        ok = services.reject_order(order_id)
        result_text = '<tg-emoji emoji-id="6300696192640620174">❌</tg-emoji> បដិសេធរួច' if ok else '<tg-emoji emoji-id="6265015769008969527">⚠️</tg-emoji> Order នេះត្រូវបានដោះស្រាយរួចហើយ'

    await query.edit_message_text(query.message.text + f"\n\n{result_text}", parse_mode="HTML")


async def _post_init(application: Application):
    from telegram import BotCommand
    await application.bot.set_my_commands([
        BotCommand("panel", "📊 Admin Panel"),
        BotCommand("help", "💬 Command ទាំងអស់"),
        BotCommand("stats", "📈 Stats"),
        BotCommand("addcoupon", "🏷️ បង្កើត Coupon"),
        BotCommand("listcoupons", "📋 មើល Coupon ទាំងអស់"),
        BotCommand("disablecoupon", "🔴 បិទ Coupon"),
        BotCommand("broadcast", "📢 ផ្សព្វផ្សាយសារ"),
    ])


@_admin_only
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        '<tg-emoji emoji-id="5462921117423384478">🛠️</tg-emoji> <b>Admin Bot — Commands:</b>\n\n'
        '/panel — <tg-emoji emoji-id="5231200819986047254">📊</tg-emoji> បើក Admin Panel (add product, approve orders, coupons)\n'
        '/stats — <tg-emoji emoji-id="6300854578149593766">📈</tg-emoji> មើលស្ថិតិលឿន (users, orders)\n'
        '/addcoupon — <tg-emoji emoji-id="5298877105000439431">🏷️</tg-emoji> បង្កើត Coupon (CODE percent|fixed AMOUNT MAX_USES)\n'
        '/listcoupons — <tg-emoji emoji-id="5987635334945444280">📋</tg-emoji> មើល Coupon ទាំងអស់\n'
        '/disablecoupon — <tg-emoji emoji-id="6170475670443922913">🔴</tg-emoji> បិទ Coupon (CODE)\n'
        '/broadcast — <tg-emoji emoji-id="6300742299114541958">📢</tg-emoji> ផ្សព្វផ្សាយសារទៅអ្នកទិញទាំងអស់\n\n'
        "🔧 Item add/edit, order approve/reject, and coupon view/close all live in /panel — "
        "this bot stays for the quick chat-only actions."
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def unknown_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.is_admin_id(update.effective_user.id):
        return
    await update.message.reply_text(
        f'<tg-emoji emoji-id="6298557526560479072">❓</tg-emoji> មិនស្គាល់ Command នេះទេ: {update.message.text}\n\nវាយ /help ដើម្បីមើល Command ទាំងអស់។',
        parse_mode="HTML")


def build_app():
    application = Application.builder().token(ADMIN_BOT_TOKEN).post_init(_post_init).build()
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("panel", panel_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("stats", stats_cmd))
    application.add_handler(CommandHandler("addcoupon", addcoupon_cmd))
    application.add_handler(CommandHandler("listcoupons", listcoupons_cmd))
    application.add_handler(CommandHandler("disablecoupon", disablecoupon_cmd))
    application.add_handler(CommandHandler("broadcast", broadcast_cmd))
    application.add_handler(CallbackQueryHandler(order_decision_callback, pattern=r"^(appr|rej)_\d+$"))
    application.add_handler(MessageHandler(filters.COMMAND, unknown_cmd))
    return application


if __name__ == "__main__":
    db.init_db()
    build_app().run_polling()
```[cite: 1, 6]
