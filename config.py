"""
config.py — Uchiro Store
All secrets come from environment variables (set these in Railway →
Variables, or in a local .env file loaded by python-dotenv for dev).
Nothing secret is hardcoded here — only sensible defaults for the
non-secret settings, so you don't have to fill in every value by hand.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ---------- Telegram bots ----------
STORE_BOT_TOKEN = os.getenv("STORE_BOT_TOKEN", "")
ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN", "")

# Comma-separated Telegram user IDs allowed to use the Admin Bot / panel.
# Get your own ID by messaging @userinfobot on Telegram.
OWNER_IDS = set(
    int(x) for x in os.getenv("OWNER_IDS", "").replace(" ", "").split(",") if x
)

# ---------- Store identity ----------
STORE_NAME = os.getenv("STORE_NAME", "Uchiro Store 🏴‍☠️")
STORE_NAME_KM = os.getenv("STORE_NAME_KM", "ហាង Uchiro")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "noreakyout")       # without the @
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "uchirostore")  # without the @
STORE_BOT_USERNAME = os.getenv("STORE_BOT_USERNAME", "UchiroStoreBot")
ADMIN_BOT_USERNAME = os.getenv("ADMIN_BOT_USERNAME", "UchiroAdminBot")

# ---------- Categories ----------
# "Account" is treated specially everywhere (single-stock, warranty,
# login/password/authenticator). Everything else is a normal stocked item.
CATEGORIES = ["Account", "Fruit", "Gamepass", "Evade", "Robux", "Blade Ball", "MM2"]

# ---------- Web app / Mini App ----------
# Your public Railway domain, e.g. https://uchiro-store.up.railway.app
# Leave blank locally — the bots will just skip the "Open App" button.
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
PORT = int(os.getenv("PORT", "8080"))

# ---------- Storage ----------
# On Railway, mount a Volume at /data and set DB_PATH=/data/store.db and
# MEDIA_DIR=/data/media so uploads and orders survive redeploys.
DB_PATH = os.getenv("DB_PATH", "store.db")
MEDIA_DIR = os.getenv("MEDIA_DIR", "media")
os.makedirs(MEDIA_DIR, exist_ok=True)

# ---------- Warranty ----------
WARRANTY_DAYS_DEFAULT = int(os.getenv("WARRANTY_DAYS_DEFAULT", "14"))
WARRANTY_DAYS_NO_AUTH = int(os.getenv("WARRANTY_DAYS_NO_AUTH", "7"))
WARRANTY_DAYS_CHOICES = [7, 14, 30]

# ---------- KHQR / Bakong (Cambodia) ----------
# These are your real merchant details, not secrets — set via env anyway
# so you don't have to touch code to change them.
BAKONG_ACCOUNT_ID = os.getenv("BAKONG_ACCOUNT_ID", "")   # e.g. your_name@wing
MERCHANT_NAME = os.getenv("MERCHANT_NAME", STORE_NAME)
MERCHANT_CITY = os.getenv("MERCHANT_CITY", "Phnom Penh")
# Real secret: get this from https://api-bakong.nbc.gov.kh (Bakong Open API).
# Without it, checkout still works but payment confirmation falls back to
# manual screenshot review by the admin instead of auto-verification.
BAKONG_API_TOKEN = os.getenv("BAKONG_API_TOKEN", "")

# ---------- Checkout ----------
ORDER_EXPIRES_MINUTES = int(os.getenv("ORDER_EXPIRES_MINUTES", "10"))  # KHQR quote window, before submission
ORDER_PENDING_TIMEOUT_HOURS = int(os.getenv("ORDER_PENDING_TIMEOUT_HOURS", "24"))  # after submission, before treated as "not confirmed"
