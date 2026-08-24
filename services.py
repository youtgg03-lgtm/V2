"""
services.py — Uchiro Store
Order approve/reject logic shared between the Admin Mini App's API
route and the Admin Bot's inline Approve/Reject buttons, so both
paths do exactly the same thing and can't drift apart.
"""

import asyncio
from telegram import Bot

import database as db
import utils
from config import STORE_BOT_TOKEN, ADMIN_USERNAME


def _send_telegram_message(chat_id, text):
    async def _send():
        bot = Bot(token=STORE_BOT_TOKEN)
        try:
            await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")
        except Exception as e:
            print(f"[notify] failed to message {chat_id}: {e}")
    try:
        asyncio.run(_send())
    except RuntimeError:
        import threading
        threading.Thread(target=lambda: asyncio.run(_send())).start()


def approve_order(order_id) -> bool:
    order = db.get_order(order_id)
    if not order or order["status"] != "pending":
        return False
    item = db.get_item(order["item_id"])
    if not item:
        return False

    db.set_order_approved(order_id)
    db.decrement_stock(order["item_id"])
    if order.get("coupon_code"):
        db.redeem_coupon(order["coupon_code"], order["buyer_chat_id"], order_id)

    msg = f'<tg-emoji emoji-id="6107318416874410520">🎉</tg-emoji> ការទូទាត់សម្រាប់ <b>{item["name"]}</b> ត្រូវបានអនុម័ត!\n\n' + utils.build_delivery_message(item)
    _send_telegram_message(order["buyer_chat_id"], msg)
    return True


def reject_order(order_id) -> bool:
    order = db.get_order(order_id)
    if not order or order["status"] != "pending":
        return False
    db.update_order_status(order_id, "rejected")
    item = db.get_item(order["item_id"])
    _send_telegram_message(
        order["buyer_chat_id"],
        f'<tg-emoji emoji-id="6300696192640620174">❌</tg-emoji> ការទូទាត់សម្រាប់ {item["name"] if item else ""} មិនត្រូវបានអនុម័តទេ។ សូមទាក់ទង @{ADMIN_USERNAME}',
    )
    return True


def notify_admins_new_order(owner_ids, order_id, item, final_price):
    from telegram import InlineKeyboardMarkup, InlineKeyboardButton
    from config import ADMIN_BOT_TOKEN

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ អនុម័ត", callback_data=f"appr_{order_id}"),
        InlineKeyboardButton("❌ បដិសេធ", callback_data=f"rej_{order_id}"),
    ]])
    text = (
        f'<tg-emoji emoji-id="6147506120920405501">🆕</tg-emoji> Order #{order_id}\n'
        f'<tg-emoji emoji-id="5854908544712707500">📦</tg-emoji> {item["name"]}\n'
        f'<tg-emoji emoji-id="6301016442582081020">💵</tg-emoji> ${final_price}'
    )

    async def _send_all():
        bot = Bot(token=ADMIN_BOT_TOKEN)
        for admin_id in owner_ids:
            try:
                if item.get("photo_path"):
                    pass
                await bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML", reply_markup=kb)
            except Exception as e:
                print(f"[notify] failed to message admin {admin_id}: {e}")

    try:
        asyncio.run(_send_all())
    except RuntimeError:
        import threading
        threading.Thread(target=lambda: asyncio.run(_send_all())).start()
