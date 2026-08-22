"""
admin_bot_additions.py
------------------------------------------------------------------
Drop-in additions for the real Uchiro Store V3 repo. Checked against
your actual database.py and admin_bot.py, so this only adds what's
genuinely missing there:

  1. /broadcast <message>  — admin_bot.py has /stats and /users
     already, but no announcement command. This adds one, sending
     via the STORE bot to every user in the `users` table (the
     same table /users already reads from).

  2. Visitor / page-view tracking — there's currently no table for
     this. Adds a `page_views` table plus a couple of query helpers
     so an admin panel "Visitors" view has something real to read.
     webapp_server.py needs one extra line per route to log a view
     (shown at the bottom) — that's the only touch point outside
     this file.

Nothing here duplicates anything that already exists (/stats,
/users, /addcoupon, /listcoupons, /disablecoupon, /release, etc.
are already in your admin_bot.py and untouched).
------------------------------------------------------------------
"""

import time
import asyncio
from telegram import Update, Bot
from telegram.ext import CommandHandler, ContextTypes

import database as db
from config import STORE_BOT_TOKEN


# ------------------------------------------------------------------
# 1. New database.py functions
#    Paste these into database.py alongside the other "Users" and
#    add-on functions — they follow the same get_conn() pattern
#    already used throughout the file.
# ------------------------------------------------------------------
"""
# ---- add to database.py: all user chat_ids, for /broadcast ----
def all_user_ids():
    with get_conn() as conn:
        rows = conn.execute("SELECT chat_id FROM users").fetchall()
        return [r["chat_id"] for r in rows]


# ---- add to database.py: page view tracking, for admin "Visitors" ----
# Add this CREATE TABLE alongside the others in init_db():
#
#   c.execute('''CREATE TABLE IF NOT EXISTS page_views (
#       id INTEGER PRIMARY KEY AUTOINCREMENT,
#       path TEXT NOT NULL,
#       chat_id INTEGER,
#       referrer TEXT,
#       viewed_at TEXT DEFAULT CURRENT_TIMESTAMP
#   )''')

def log_page_view(path, chat_id=None, referrer=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO page_views (path, chat_id, referrer) VALUES (?, ?, ?)",
            (path, chat_id, referrer),
        )

def count_views_since(hours=24):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) c FROM page_views WHERE viewed_at >= datetime('now', ?)",
            (f'-{hours} hours',),
        ).fetchone()
        return row["c"]

def count_unique_visitors_since(hours=24):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(DISTINCT chat_id) c FROM page_views "
            "WHERE viewed_at >= datetime('now', ?) AND chat_id IS NOT NULL",
            (f'-{hours} hours',),
        ).fetchone()
        return row["c"]

def top_pages(limit=5):
    with get_conn() as conn:
        return conn.execute(
            "SELECT path, COUNT(*) views FROM page_views "
            "GROUP BY path ORDER BY views DESC LIMIT ?",
            (limit,),
        ).fetchall()

def views_by_day(days=7):
    with get_conn() as conn:
        return conn.execute(
            "SELECT date(viewed_at) day, COUNT(*) views FROM page_views "
            "WHERE viewed_at >= datetime('now', ?) "
            "GROUP BY date(viewed_at) ORDER BY day",
            (f'-{days} days',),
        ).fetchall()
"""


# ------------------------------------------------------------------
# 2. /broadcast — owner/admin only, sends through the store bot
#    since that's the bot your buyers actually have open.
#    Usage: /broadcast <message>
# ------------------------------------------------------------------
async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db.is_admin_id(update.effective_user.id):
        return await update.message.reply_text("អ្នកមិនមែនជា Admin ទេ។")

    message_text = " ".join(context.args) if context.args else None
    if not message_text:
        return await update.message.reply_text(
            "ប្រើ: /broadcast <សារ>\n\n"
            "ឧ. /broadcast 🎉 មានទំនិញថ្មី! Dragon Fruit x5 មកដល់ហើយ — ចូលមើលឥឡូវ"
        )

    user_ids = db.all_user_ids()  # add all_user_ids() to database.py first, see above
    await update.message.reply_text(f"កំពុងផ្ញើទៅអ្នកប្រើប្រាស់ {len(user_ids)} នាក់…")

    store_bot = Bot(token=STORE_BOT_TOKEN)
    sent, failed = 0, 0
    batch_size = 25  # stay comfortably under Telegram's ~30 msg/sec limit

    for i in range(0, len(user_ids), batch_size):
        batch = user_ids[i:i + batch_size]
        for chat_id in batch:
            try:
                await store_bot.send_message(chat_id, f"📢 {message_text}")
                sent += 1
            except Exception:
                # user blocked the bot / deleted their account — skip, keep going
                failed += 1
        await asyncio.sleep(1)

    await update.message.reply_text(f"✅ ផ្ញើរួច។ ជោគជ័យ: {sent}, បរាជ័យ/Block bot: {failed}")


# ------------------------------------------------------------------
# 3. Register in admin_bot.py's build_app(), next to the other
#    app.add_handler(CommandHandler(...)) lines:
#
#       from admin_bot_additions import broadcast_cmd
#       app.add_handler(CommandHandler("broadcast", broadcast_cmd))
#
#    And add a line to the /start help text alongside the other
#    command groups, e.g. under "🛠 គ្រប់គ្រង":
#       "/broadcast <សារ> - ផ្ញើសារទៅអ្នកប្រើប្រាស់ទាំងអស់"
# ------------------------------------------------------------------


# ------------------------------------------------------------------
# 4. webapp_server.py touch point (for the Visitors admin view)
#    Add one line to whatever route serves each Mini App page —
#    right where it already reads the Telegram WebApp initData:
#
#       db.log_page_view(request.path, chat_id=verified_chat_id,
#                         referrer=request.headers.get("referer"))
#
#    Since every request there is already HMAC-verified via
#    initData (per your README), chat_id is trustworthy — no
#    separate auth needed for this logging call.
# ------------------------------------------------------------------
