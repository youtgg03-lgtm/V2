"""
database.py — Uchiro Store
SQLite storage for items, orders, users, and coupons. Every function
opens and closes its own connection (safe for both the bots and the
Flask app calling in from different threads).
"""

import sqlite3
import time
import secrets
from contextlib import contextmanager

from config import DB_PATH, OWNER_IDS


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT DEFAULT '',
            quantity INTEGER NOT NULL DEFAULT 0,
            warranty_days INTEGER NOT NULL DEFAULT 0,
            delivery_info TEXT DEFAULT '',
            totp_secret TEXT DEFAULT '',
            photo_path TEXT DEFAULT '',
            video_path TEXT DEFAULT '',
            is_new INTEGER NOT NULL DEFAULT 1,
            published INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            buyer_chat_id INTEGER NOT NULL,
            price REAL NOT NULL,
            final_price REAL NOT NULL,
            coupon_code TEXT DEFAULT '',
            khqr_md5 TEXT DEFAULT '',
            payment_photo_path TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            source TEXT NOT NULL DEFAULT 'webapp',
            warranty_days INTEGER NOT NULL DEFAULT 0,
            warranty_expires_at INTEGER,
            created_at INTEGER NOT NULL,
            FOREIGN KEY (item_id) REFERENCES items(id)
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            username TEXT,
            lang TEXT DEFAULT 'km',
            first_seen INTEGER,
            last_seen INTEGER
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS coupons (
            code TEXT PRIMARY KEY,
            discount_type TEXT NOT NULL,      -- 'percent' or 'fixed'
            amount REAL NOT NULL,
            max_uses INTEGER NOT NULL DEFAULT 1,
            used_count INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            created_at INTEGER NOT NULL
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS coupon_redemptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL,
            buyer_chat_id INTEGER NOT NULL,
            order_id INTEGER,
            redeemed_at INTEGER NOT NULL,
            UNIQUE(code, buyer_chat_id)
        )""")

        conn.execute("""CREATE TABLE IF NOT EXISTS page_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            chat_id INTEGER,
            viewed_at INTEGER NOT NULL
        )""")


def is_admin_id(chat_id: int) -> bool:
    return int(chat_id) in OWNER_IDS


# ============================================================
# ITEMS
# ============================================================
def add_item(category, name, price, description="", quantity=0, warranty_days=0,
             delivery_info="", totp_secret="", photo_path="", video_path="",
             published=0):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO items (category, name, price, description, quantity,
               warranty_days, delivery_info, totp_secret, photo_path, video_path,
               is_new, published, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,1,?,?)""",
            (category, name, price, description, quantity, warranty_days,
             delivery_info, totp_secret, photo_path, video_path,
             published, int(time.time())),
        )
        return cur.lastrowid


def get_item(item_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        return dict(row) if row else None


def list_published_items(category=None):
    with get_conn() as conn:
        if category and category != "all":
            rows = conn.execute(
                "SELECT * FROM items WHERE published=1 AND category=? ORDER BY created_at DESC",
                (category,)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM items WHERE published=1 ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def list_all_items():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM items ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def decrement_stock(item_id, by=1):
    with get_conn() as conn:
        conn.execute("UPDATE items SET quantity = MAX(quantity - ?, 0) WHERE id=?", (by, item_id))
        # Auto-close: once stock hits 0, unpublish so it disappears from the shop.
        conn.execute("UPDATE items SET published=0 WHERE id=? AND quantity<=0", (item_id,))


def release_all_drafts():
    with get_conn() as conn:
        cur = conn.execute("UPDATE items SET published=1 WHERE published=0")
        return cur.rowcount


def delete_item(item_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM items WHERE id=?", (item_id,))


# ============================================================
# USERS
# ============================================================
def touch_user(chat_id, username=None, lang=None):
    now = int(time.time())
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users (chat_id, username, lang, first_seen, last_seen)
            VALUES (?,?,COALESCE(?, 'km'),?,?)
            ON CONFLICT(chat_id) DO UPDATE SET
                username=excluded.username,
                last_seen=excluded.last_seen,
                lang=COALESCE(?, users.lang)
        """, (chat_id, username, lang, now, now, lang))


def get_user_lang(chat_id):
    with get_conn() as conn:
        row = conn.execute("SELECT lang FROM users WHERE chat_id=?", (chat_id,)).fetchone()
        return row["lang"] if row else "km"


def count_users():
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]


def all_user_ids():
    with get_conn() as conn:
        return [r["chat_id"] for r in conn.execute("SELECT chat_id FROM users").fetchall()]


# ============================================================
# ORDERS
# ============================================================
def create_order(item_id, buyer_chat_id, price, final_price, coupon_code="",
                  khqr_md5="", payment_photo_path="", warranty_days=0, source="webapp"):
    now = int(time.time())
    expires_at = now + warranty_days * 86400 if warranty_days else None
    with get_conn() as conn:
        cur = conn.execute("""
            INSERT INTO orders (item_id, buyer_chat_id, price, final_price, coupon_code,
                khqr_md5, payment_photo_path, status, source, warranty_days,
                warranty_expires_at, created_at)
            VALUES (?,?,?,?,?,?,?,'pending',?,?,?,?)
        """, (item_id, buyer_chat_id, price, final_price, coupon_code, khqr_md5,
              payment_photo_path, source, warranty_days, expires_at, now))
        return cur.lastrowid


def get_order(order_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        return dict(row) if row else None


def get_orders_by_buyer(chat_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM orders WHERE buyer_chat_id=? ORDER BY created_at DESC",
            (chat_id,)).fetchall()
        return [dict(r) for r in rows]


def list_orders(status=None):
    with get_conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM orders WHERE status=? ORDER BY created_at DESC", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM orders ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def set_order_approved(order_id):
    with get_conn() as conn:
        # (re)set warranty clock at the moment of approval/delivery, not submission
        order = conn.execute("SELECT warranty_days FROM orders WHERE id=?", (order_id,)).fetchone()
        expires_at = int(time.time()) + order["warranty_days"] * 86400 if order and order["warranty_days"] else None
        conn.execute(
            "UPDATE orders SET status='approved', warranty_expires_at=? WHERE id=?",
            (expires_at, order_id))


def update_order_status(order_id, status):
    with get_conn() as conn:
        conn.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))


def count_orders_by_status():
    with get_conn() as conn:
        rows = conn.execute("SELECT status, COUNT(*) c FROM orders GROUP BY status").fetchall()
        return {r["status"]: r["c"] for r in rows}


# ============================================================
# COUPONS
# ============================================================
def add_coupon(code, discount_type, amount, max_uses):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO coupons (code, discount_type, amount, max_uses, used_count, active, created_at)
            VALUES (?,?,?,?,0,1,?)
            ON CONFLICT(code) DO UPDATE SET
                discount_type=excluded.discount_type, amount=excluded.amount,
                max_uses=excluded.max_uses, active=1
        """, (code.upper(), discount_type, amount, max_uses, int(time.time())))


def list_coupons():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM coupons ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_coupon(code):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM coupons WHERE code=?", (code.upper(),)).fetchone()
        return dict(row) if row else None


def disable_coupon(code):
    with get_conn() as conn:
        conn.execute("UPDATE coupons SET active=0 WHERE code=?", (code.upper(),))


def validate_coupon(code, buyer_chat_id, item_price):
    """Returns {"valid": bool, "discounted_price": float, "label": str, "error": str}"""
    coupon = get_coupon(code)
    if not coupon or not coupon["active"]:
        return {"valid": False, "error": "Coupon not found or disabled / លេខកូដមិនត្រឹមត្រូវ"}
    if coupon["used_count"] >= coupon["max_uses"]:
        return {"valid": False, "error": "Coupon limit reached / លេខកូដប្រើអស់ហើយ"}
    with get_conn() as conn:
        already = conn.execute(
            "SELECT 1 FROM coupon_redemptions WHERE code=? AND buyer_chat_id=?",
            (coupon["code"], buyer_chat_id)).fetchone()
    if already:
        return {"valid": False, "error": "You've already used this coupon / អ្នកបានប្រើលេខកូដនេះរួចហើយ"}

    if coupon["discount_type"] == "percent":
        discounted = round(item_price * (1 - coupon["amount"] / 100), 2)
        label = f"{coupon['amount']:.0f}% off"
    else:
        discounted = round(max(item_price - coupon["amount"], 0), 2)
        label = f"${coupon['amount']:.2f} off"
    return {"valid": True, "discounted_price": discounted, "label": label}


def redeem_coupon(code, buyer_chat_id, order_id):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO coupon_redemptions (code, buyer_chat_id, order_id, redeemed_at) VALUES (?,?,?,?)",
            (code.upper(), buyer_chat_id, order_id, int(time.time())))
        conn.execute("UPDATE coupons SET used_count = used_count + 1 WHERE code=?", (code.upper(),))


# ============================================================
# PAGE VIEWS (lightweight analytics, optional)
# ============================================================
def log_page_view(path, chat_id=None):
    with get_conn() as conn:
        conn.execute("INSERT INTO page_views (path, chat_id, viewed_at) VALUES (?,?,?)",
                     (path, chat_id, int(time.time())))
