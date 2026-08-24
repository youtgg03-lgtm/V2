"""
webapp_server.py — Uchiro Store
Serves the Store Mini App (/) and Admin Mini App (/admin), plus the
JSON API both call. Payment auto-confirms via Bakong KHQR when
BAKONG_API_TOKEN is configured; otherwise orders wait for manual
admin approval (bot or panel) — either path works end to end.
"""

import os
import time

from flask import Flask, request, jsonify, render_template, send_from_directory

import database as db
import utils
import services
from config import (
    STORE_BOT_TOKEN, ADMIN_BOT_TOKEN, WEBAPP_URL, MEDIA_DIR,
    ADMIN_USERNAME, CHANNEL_USERNAME, ORDER_EXPIRES_MINUTES, ORDER_PENDING_TIMEOUT_HOURS,
    WARRANTY_DAYS_NO_AUTH, CATEGORIES,
)

app = Flask(
    __name__,
    template_folder=os.path.join("webapp", "templates"),
    static_folder=None,  # we serve assets ourselves via /assets/<file>
)
db.init_db()

LOGO_URL = f"{WEBAPP_URL}/media/logo.png" if WEBAPP_URL and os.path.exists(os.path.join(MEDIA_DIR, "logo.png")) else ""
MUSIC_URL = f"{WEBAPP_URL}/media/music.mp3" if WEBAPP_URL and os.path.exists(os.path.join(MEDIA_DIR, "music.mp3")) else ""


# ============================================================
# Static file routes (Jinja templates reference these by name
# via url_for('assets', filename=...) / url_for('media', filename=...))
# ============================================================
@app.route("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(os.path.join("webapp", "assets"), filename)


@app.route("/media/<path:filename>")
def media(filename):
    return send_from_directory(MEDIA_DIR, filename)


@app.route("/health")
def health():
    return jsonify({"ok": True})


# ============================================================
# Page routes
# ============================================================
@app.route("/")
def index():
    return render_template(
        "index.html",
        admin_username=ADMIN_USERNAME,
        channel_username=CHANNEL_USERNAME,
        logo_url=LOGO_URL,
        music_url=MUSIC_URL,
    )


@app.route("/admin")
def admin_page():
    return render_template("admin.html", categories=CATEGORIES)


# ============================================================
# Auth helper
# ============================================================
def _auth_store_user(init_data):
    return utils.verify_webapp_init_data(init_data, STORE_BOT_TOKEN)


def _auth_admin(init_data):
    user = utils.verify_webapp_init_data(init_data, ADMIN_BOT_TOKEN)
    if not user or not db.is_admin_id(user["id"]):
        return None
    return user


def _item_public_dict(item):
    return {
        "id": item["id"], "category": item["category"], "name": item["name"],
        "price": item["price"], "description": item["description"],
        "quantity": item["quantity"], "warranty_days": item["warranty_days"],
        "is_new": bool(item["is_new"]),
        "photo_url": f"/media/{item['photo_path']}" if item["photo_path"] else "",
    }


# ============================================================
# API — catalog
# ============================================================
@app.route("/api/items")
def api_items():
    category = request.args.get("category")
    items = db.list_published_items(category)
    return jsonify({"items": [_item_public_dict(i) for i in items], "categories": CATEGORIES})


@app.route("/api/rules")
def api_rules():
    return jsonify({
        "warranty_standard": 14,
        "warranty_no_auth": WARRANTY_DAYS_NO_AUTH,
        "warranty_none": 0,
        "text_km": "Warranty 14ថ្ងៃ លើគណនីទាំងអស់។ បើលុប Authenticator App: 7ថ្ងៃ។ បើលុប Email+Code ទាំងអស់: គ្មាន Warranty។",
    })


# ============================================================
# API — checkout
# ============================================================
@app.route("/api/order/quote", methods=["POST"])
def api_order_quote():
    body = request.get_json(force=True) or {}
    item = db.get_item(body.get("item_id"))
    if not item or not item["published"]:
        return jsonify({"error": "Item not available"}), 404

    total = item["price"]
    coupon_valid, coupon_error, discount_applied = True, None, None
    coupon_code = (body.get("coupon_code") or "").strip().upper()
    user = _auth_store_user(body.get("init_data", "")) or {}
    buyer_id = user.get("id", 0)

    if coupon_code:
        result = db.validate_coupon(coupon_code, buyer_id, item["price"])
        if result["valid"]:
            total = result["discounted_price"]
            discount_applied = result["label"]
        else:
            coupon_valid = False
            coupon_error = result["error"]
            coupon_code = ""

    bill_number = f"UCH{item['id']}{int(time.time())}"
    img_name = f"qr_{bill_number}.png"
    img_path = os.path.join(MEDIA_DIR, img_name)
    qr_string, md5_hash, saved_path = utils.generate_khqr(total, bill_number, out_path=img_path)
    qr_url = f"/media/{img_name}" if saved_path else ""

    return jsonify({
        "item_id": item["id"], "name": item["name"], "price": item["price"],
        "total": total, "warranty_days": item["warranty_days"],
        "qr_url": qr_url, "khqr_md5": md5_hash or "",
        "coupon_valid": coupon_valid, "coupon_error": coupon_error,
        "discount_applied": discount_applied,
        "note": "" if qr_url else "KHQR មិនទាន់បានកំណត់ — សូមទាក់ទង Admin ដើម្បីទូទាត់ផ្ទាល់",
    })


@app.route("/api/order/submit", methods=["POST"])
def api_order_submit():
    init_data = request.form.get("init_data", "")
    user = _auth_store_user(init_data)
    if not user:
        return jsonify({"error": "unauthorized"}), 403

    item_id = request.form.get("item_id")
    item = db.get_item(item_id)
    if not item or not item["published"] or item["quantity"] <= 0:
        return jsonify({"error": "Item not available / ទំនិញអស់ស្តុក"}), 400

    khqr_md5 = request.form.get("khqr_md5", "")
    coupon_code = (request.form.get("coupon_code") or "").strip().upper()
    final_price = item["price"]
    if coupon_code:
        result = db.validate_coupon(coupon_code, user["id"], item["price"])
        if result["valid"]:
            final_price = result["discounted_price"]
        else:
            coupon_code = ""  # silently drop an invalid code rather than failing the whole order

    photo = request.files.get("photo")
    photo_path = utils.save_uploaded_file(photo, subdir="payments") if photo else ""
    if not photo_path and not khqr_md5:
        return jsonify({"error": "Upload a payment screenshot / សូម Upload រូបភាពទូទាត់"}), 400

    db.touch_user(user["id"], user.get("username"))
    order_id = db.create_order(
        item_id=item["id"], buyer_chat_id=user["id"], price=item["price"],
        final_price=final_price, coupon_code=coupon_code, khqr_md5=khqr_md5,
        payment_photo_path=photo_path, warranty_days=item["warranty_days"], source="webapp",
    )

    # notify admins WITH inline Approve/Reject buttons — falls back gracefully
    # if KHQR auto-confirms this order before anyone taps a button
    services.notify_admins_new_order(_owner_ids_safe(), order_id, item, final_price)

    return jsonify({"order_id": order_id})


def _owner_ids_safe():
    from config import OWNER_IDS
    return list(OWNER_IDS)


@app.route("/api/order/<int:order_id>/status")
def api_order_status(order_id):
    user = _auth_store_user(request.args.get("init_data", ""))
    order = db.get_order(order_id)
    if not order or not user or order["buyer_chat_id"] != user["id"]:
        return jsonify({"error": "not found"}), 404

    # After 24h with no admin decision, tell the buyer plainly this isn't confirmed
    # yet — without silently rejecting it, so an admin can still approve it late
    # if the payment genuinely did come through.
    is_stale = (
        order["status"] == "pending"
        and (time.time() - order["created_at"]) > ORDER_PENDING_TIMEOUT_HOURS * 3600
    )

    # auto-check KHQR payment if this order used one
    if order["status"] == "pending" and order["khqr_md5"]:
        if utils.check_khqr_paid(order["khqr_md5"]):
            services.approve_order(order_id)
            order = db.get_order(order_id)
            is_stale = False

    item = db.get_item(order["item_id"])
    fields = utils.get_delivery_fields(item) if order["status"] == "approved" and item else {}
    return jsonify({
        "status": order["status"],
        "is_stale": is_stale,
        "item_name": item["name"] if item else "",
        "delivery_info": utils.build_delivery_message(item) if order["status"] == "approved" and item else "",
        "fields": fields,  # {login_name, login_password, totp_secret, delivery_note, has_totp}
        "has_totp": utils.has_totp(item) if item else False,
        "warranty_expires_at": (
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(order["warranty_expires_at"]))
            if order["warranty_expires_at"] else None
        ),
    })


@app.route("/api/order/<int:order_id>/refresh-code")
def api_order_refresh_code(order_id):
    user = _auth_store_user(request.args.get("init_data", ""))
    order = db.get_order(order_id)
    if not order or not user or order["buyer_chat_id"] != user["id"] or order["status"] != "approved":
        return jsonify({"error": "not found"}), 404
    item = db.get_item(order["item_id"])
    if not item or not item["totp_secret"]:
        return jsonify({"error": "no authenticator on this order"}), 400
    return jsonify({"code": utils.generate_totp_code(item["totp_secret"])})


@app.route("/api/my-orders")
def api_my_orders():
    user = _auth_store_user(request.args.get("init_data", ""))
    if not user:
        return jsonify({"error": "unauthorized"}), 403
    orders = db.get_orders_by_buyer(user["id"])
    out = []
    for o in orders:
        item = db.get_item(o["item_id"])
        out.append({
            "id": o["id"], "item_name": item["name"] if item else "?",
            "status": o["status"], "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(o["created_at"])),
            "warranty": f"{o['warranty_days']}d warranty" if o["warranty_days"] else None,
            "is_stale": o["status"] == "pending" and (time.time() - o["created_at"]) > ORDER_PENDING_TIMEOUT_HOURS * 3600,
        })
    return jsonify({"orders": out})


# ============================================================
# API — admin
# ============================================================
@app.route("/api/admin/verify", methods=["POST"])
def api_admin_verify():
    body = request.get_json(force=True) or {}
    user = _auth_admin(body.get("init_data", ""))
    return jsonify({"ok": bool(user)})


@app.route("/api/admin/items", methods=["GET", "POST"])
def api_admin_items():
    if request.method == "GET":
        user = _auth_admin(request.args.get("init_data", ""))
        if not user:
            return jsonify({"error": "unauthorized"}), 403
        return jsonify({"items": db.list_all_items()})

    # POST — create item (multipart form: covers both Account and Item flows)
    user = _auth_admin(request.form.get("init_data", ""))
    if not user:
        return jsonify({"error": "unauthorized"}), 403

    category = request.form.get("category", "")
    name = request.form.get("name", "")
    price = float(request.form.get("price", 0))
    is_account = category == "Account"

    photo = request.files.get("photo")
    video = request.files.get("video")
    photo_path = utils.save_uploaded_file(photo, subdir="items") if photo else ""
    video_path = utils.save_uploaded_file(video, subdir="items") if video else ""

    item_id = db.add_item(
        category=category, name=name, price=price,
        description=request.form.get("description", ""),
        quantity=1 if is_account else int(request.form.get("quantity", 0)),
        warranty_days=int(request.form.get("warranty_days", 14)) if is_account else 0,
        login_name=request.form.get("login_name", ""),
        login_password=request.form.get("login_password", ""),
        delivery_info=request.form.get("delivery_info", ""),  # generic note, mainly for trade items
        totp_secret=request.form.get("totp_secret", ""),
        photo_path=photo_path, video_path=video_path,
        published=0,  # always starts as a draft — release via /release or the panel
    )
    return jsonify({"item_id": item_id})


@app.route("/api/admin/items/<int:item_id>", methods=["PATCH", "DELETE"])
def api_admin_item_detail(item_id):
    init_data = request.form.get("init_data") or (request.get_json(silent=True) or {}).get("init_data", "")
    user = _auth_admin(init_data)
    if not user:
        return jsonify({"error": "unauthorized"}), 403

    if request.method == "DELETE":
        db.delete_item(item_id)
        return jsonify({"ok": True})

    # PATCH — not fully implemented; add fields as needed via database.py
    return jsonify({"error": "not implemented — extend database.py with an update_item() function"}), 501


@app.route("/api/admin/items/release-all", methods=["POST"])
def api_admin_release_all():
    body = request.get_json(force=True) or {}
    user = _auth_admin(body.get("init_data", ""))
    if not user:
        return jsonify({"error": "unauthorized"}), 403
    count = db.release_all_drafts()
    return jsonify({"released": count})


@app.route("/api/admin/orders")
def api_admin_orders():
    user = _auth_admin(request.args.get("init_data", ""))
    if not user:
        return jsonify({"error": "unauthorized"}), 403
    orders = db.list_orders()
    out = []
    for o in orders:
        out.append({**o, "payment_photo_url": f"/media/{o['payment_photo_path']}" if o["payment_photo_path"] else ""})
    return jsonify({"orders": out})


@app.route("/api/admin/orders/<int:order_id>/<action>", methods=["POST"])
def api_admin_order_decision(order_id, action):
    if action not in ("appr", "rej"):
        return jsonify({"error": "invalid action"}), 400
    body = request.get_json(force=True) or {}
    user = _auth_admin(body.get("init_data", ""))
    if not user:
        return jsonify({"error": "unauthorized"}), 403

    order = db.get_order(order_id)
    if not order or order["status"] != "pending":
        return jsonify({"error": "already handled"}), 400

    if action == "appr":
        services.approve_order(order_id)
    else:
        services.reject_order(order_id)
    return jsonify({"ok": True})


@app.route("/api/admin/coupons")
def api_admin_coupons():
    user = _auth_admin(request.args.get("init_data", ""))
    if not user:
        return jsonify({"error": "unauthorized"}), 403
    return jsonify({"coupons": db.list_coupons()})


@app.route("/api/admin/coupons/disable", methods=["POST"])
def api_admin_disable_coupon():
    body = request.get_json(force=True) or {}
    user = _auth_admin(body.get("init_data", ""))
    if not user:
        return jsonify({"error": "unauthorized"}), 403
    code = body.get("code", "")
    if not code:
        return jsonify({"error": "code required"}), 400
    db.disable_coupon(code)
    return jsonify({"ok": True})


if __name__ == "__main__":
    from config import PORT
    app.run(host="0.0.0.0", port=PORT, debug=False)
