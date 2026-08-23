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
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

import database as db
import services
from config import ADMIN_BOT_TOKEN, STORE_BOT_TOKEN, WEBAPP_URL

logging.basicConfig(level=logging.INFO)


def _admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not db.is_admin_id(update.effective_user.id):
            return await update.message.reply_text("🚫 Owner only.")
        return await func(update, context)
    return wrapper


@_admin_only
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await panel_cmd(update, context)


@_admin_only
async def panel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not WEBAPP_URL:
        return await update.message.reply_text("⚠️ WEBAPP_URL not set — deploy first, then this button will work.")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(
        "📊 Open Admin Panel", web_app=WebAppInfo(url=f"{WEBAPP_URL}/admin"))]])
    await update.message.reply_text(
        "🛠️ Admin Panel — add products, approve orders, manage coupons, all here:",
        reply_markup=kb)


@_admin_only
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_users = db.count_users()
    by_status = db.count_orders_by_status()
    text = (
        f"📊 *Uchiro Store stats*\n\n"
        f"👥 Users: `{total_users}`\n"
        f"⏳ Pending orders: `{by_status.get('pending', 0)}`\n"
        f"✅ Approved orders: `{by_status.get('approved', 0)}`\n"
        f"❌ Rejected: `{by_status.get('rejected', 0)}`\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


@_admin_only
async def addcoupon_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /addcoupon CODE percent|fixed AMOUNT MAX_USES
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
    await update.message.reply_text(f"✅ Coupon {code.upper()} បានបង្កើត — មើល/បិទបានក្នុង Panel ដែរ។")


@_admin_only
async def listcoupons_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coupons = db.list_coupons()
    if not coupons:
        return await update.message.reply_text("គ្មាន Coupon ទេ។")
    lines = [
        f"{'🟢' if c['active'] else '🔴'} `{c['code']}` — "
        f"{c['amount']:.0f}{'%' if c['discount_type']=='percent' else '$'} off "
        f"({c['used_count']}/{c['max_uses']})"
        for c in coupons
    ]
    await update.message.reply_text("🏷️ *Coupons:*\n" + "\n".join(lines), parse_mode="Markdown")


@_admin_only
async def disablecoupon_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("ប្រើ: /disablecoupon CODE")
    db.disable_coupon(context.args[0])
    await update.message.reply_text(f"🔴 Coupon {context.args[0].upper()} បិទរួច។")


@_admin_only
async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = " ".join(context.args) if context.args else None
    if not message_text:
        return await update.message.reply_text(
            "ប្រើ: /broadcast <សារ>\n\nឧ. /broadcast 🎉 មានទំនិញថ្មី! ចូលមើលឥឡូវ")

    user_ids = db.all_user_ids()
    await update.message.reply_text(f"កំពុងផ្ញើទៅ {len(user_ids)} នាក់…")

    store_bot = Bot(token=STORE_BOT_TOKEN)
    sent, failed = 0, 0
    for i in range(0, len(user_ids), 25):
        for uid in user_ids[i:i + 25]:
            try:
                await store_bot.send_message(uid, f"📢 {message_text}")
                sent += 1
            except Exception:
                failed += 1
        await asyncio.sleep(1)
    await update.message.reply_text(f"✅ ជោគជ័យ: {sent}, បរាជ័យ: {failed}")


async def order_decision_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the ✅/❌ buttons on the order notification message. Uses the
    exact same services.approve_order/reject_order the panel calls, so a
    decision made here or in the panel can never disagree with each other."""
    query = update.callback_query
    await query.answer()
    if not db.is_admin_id(query.from_user.id):
        return await query.answer("Owner only.", show_alert=True)

    action, order_id_str = query.data.split("_", 1)
    order_id = int(order_id_str)

    if action == "appr":
        ok = services.approve_order(order_id)
        result_text = "✅ អនុម័តរួច — ប្រគល់ជូនរួច" if ok else "⚠️ Order នេះត្រូវបានដោះស្រាយរួចហើយ"
    else:
        ok = services.reject_order(order_id)
        result_text = "❌ បដិសេធរួច" if ok else "⚠️ Order នេះត្រូវបានដោះស្រាយរួចហើយ"

    await query.edit_message_text(query.message.text + f"\n\n{result_text}")


async def _post_init(application: Application):
    from telegram import BotCommand
    await application.bot.set_my_commands([
        BotCommand("panel", "📊 Admin Panel"),
        BotCommand("stats", "📈 Stats"),
        BotCommand("addcoupon", "🏷️ បង្កើត Coupon"),
        BotCommand("listcoupons", "📋 មើល Coupon ទាំងអស់"),
        BotCommand("disablecoupon", "🔴 បិទ Coupon"),
        BotCommand("broadcast", "📢 ផ្សព្វផ្សាយសារ"),
    ])


def build_app():
    application = Application.builder().token(ADMIN_BOT_TOKEN).post_init(_post_init).build()
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("panel", panel_cmd))
    application.add_handler(CommandHandler("stats", stats_cmd))
    application.add_handler(CommandHandler("addcoupon", addcoupon_cmd))
    application.add_handler(CommandHandler("listcoupons", listcoupons_cmd))
    application.add_handler(CommandHandler("disablecoupon", disablecoupon_cmd))
    application.add_handler(CommandHandler("broadcast", broadcast_cmd))
    application.add_handler(CallbackQueryHandler(order_decision_callback, pattern=r"^(appr|rej)_\d+$"))
    return application


if __name__ == "__main__":
    db.init_db()
    build_app().run_polling()
