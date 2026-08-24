"""
utils.py — Uchiro Store
Shared helpers used by both webapp_server.py and the two bots.
"""

import hashlib
import hmac
import json
import time
import uuid
from urllib.parse import parse_qsl

import pyotp

from config import (
    BAKONG_ACCOUNT_ID, MERCHANT_NAME, MERCHANT_CITY, BAKONG_API_TOKEN,
    MEDIA_DIR, WARRANTY_DAYS_NO_AUTH,
)


def verify_webapp_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400):
    if not init_data or not bot_token:
        return None
    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
        received_hash = pairs.pop("hash", None)
        if not received_hash:
            return None

        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(computed_hash, received_hash):
            return None

        auth_date = int(pairs.get("auth_date", "0"))
        if max_age_seconds and (time.time() - auth_date) > max_age_seconds:
            return None

        user = json.loads(pairs.get("user", "{}"))
        return user if user.get("id") else None
    except Exception:
        return None


def generate_totp_code(secret: str) -> str:
    if not secret:
        return ""
    return pyotp.TOTP(secret.replace(" ", "").upper()).now()


def build_delivery_message(item: dict) -> str:
    """HTML-formatted version, used for the Telegram bot chat message with premium emojis."""
    lines = []
    if item["category"] == "Account":
        if item.get("login_name") or item.get("login_password"):
            if item.get("login_name"):
                lines.append(f'<tg-emoji emoji-id="5258011929993026890">👤</tg-emoji> Name: <code>{item["login_name"]}</code>')
            if item.get("login_password"):
                lines.append(f'<tg-emoji emoji-id="5420094143089111506">🔑</tg-emoji> Password: <code>{item["login_password"]}</code>')
        elif item.get("delivery_info"):
            lines.append(item["delivery_info"])
        if item.get("totp_secret"):
            secret = item["totp_secret"].replace(" ", "").upper()
            lines.append(f'\n<tg-emoji emoji-id="6109136102868652214">🔐</tg-emoji> Authenticator Setup Key (វាយបញ្ចូល App ដោយខ្លួនឯង):\n<code>{secret}</code>')
            lines.append(
                '\n<tg-emoji emoji-id="5470177992950946662">👉</tg-emoji> បើកលឿន? Copy លេខកូដ 6 ខ្ទង់ដែលកំពុង Live ក្នុង App ដោយផ្ទាល់ '
                "(មិនចាំបាច់ដំឡើង Authenticator ខ្លួនឯងទេ)\n"
                f'<tg-emoji emoji-id="6109136102868652214">🔐</tg-emoji> លេខកូដឥឡូវនេះ: <code>{generate_totp_code(item["totp_secret"])}</code>'
            )
            lines.append("(ចូល Telegram → ការបញ្ជាទិញរបស់ខ្ញុំ → Refresh ដើម្បីទទួលបានលេខកូដថ្មីរាល់ 30 វិនាទី)")
        warranty = item.get("warranty_days") or WARRANTY_DAYS_NO_AUTH
        lines.append(f'\n<tg-emoji emoji-id="5251203410396458957">🛡️</tg-emoji> Warranty: {warranty} ថ្ងៃ គិតពីពេលទទួល')
    else:
        if item.get("delivery_info"):
            lines.append(item["delivery_info"])
        else:
            lines.append("ទំនិញនេះនឹងប្រគល់ជូនផ្ទាល់ក្នុងហ្គេម — Admin នឹងទាក់ទងអ្នកឆាប់ៗនេះ។")
    return "\n".join(lines)


def get_delivery_fields(item: dict) -> dict:
    return {
        "login_name": item.get("login_name") or "",
        "login_password": item.get("login_password") or "",
        "totp_secret": (item.get("totp_secret") or "").replace(" ", "").upper(),
        "delivery_note": item.get("delivery_info") or "",
        "has_totp": has_totp(item),
    }


def has_totp(item: dict) -> bool:
    return bool(item.get("totp_secret"))


def save_uploaded_file(file_storage, subdir="") -> str:
    if not file_storage or not file_storage.filename:
        return ""
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else "bin"
    name = f"{uuid.uuid4().hex}.{ext}"
    import os
    folder = os.path.join(MEDIA_DIR, subdir) if subdir else MEDIA_DIR
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    file_storage.save(path)
    return os.path.join(subdir, name) if subdir else name


def generate_khqr(amount: float, bill_number: str, out_path: str = None):
    if not BAKONG_ACCOUNT_ID:
        return None, None, None
    try:
        from bakong_khqr import KHQR
        khqr = KHQR(BAKONG_API_TOKEN or None)
        qr_string = khqr.create_qr(
            account_id=BAKONG_ACCOUNT_ID,
            merchant_name=MERCHANT_NAME,
            merchant_city=MERCHANT_CITY,
            amount=amount,
            currency="USD",
            store_label=MERCHANT_NAME,
            bill_number=bill_number,
        )
        md5_hash = khqr.generate_md5(qr_string)
        image_path = None
        if out_path:
            image_path = khqr.qr_image(qr_string, format="png", output_path=out_path)
        return qr_string, md5_hash, image_path
    except Exception as e:
        print(f"[khqr] generation failed: {e}")
        return None, None, None


def check_khqr_paid(md5_hash: str) -> bool:
    if not BAKONG_API_TOKEN or not md5_hash:
        return False
    try:
        from bakong_khqr import KHQR
        khqr = KHQR(BAKONG_API_TOKEN)
        result = khqr.check_payment(md5_hash)
        return result == "PAID"
    except Exception as e:
        print(f"[khqr] payment check failed: {e}")
        return False
