# Uchiro Store — complete, ready to run

Everything in one place: two bots, one web server, one database, two Mini Apps.
This is a fresh, complete implementation — not a patch on top of another repo —
built to everything discussed: KH/EN Mini App with category filters, big warranty
badges, zoom, coupon checkout, real KHQR + auto-delivery, live authenticator codes,
live warranty countdown, and an admin panel that does the heavy lifting so the bots
stay minimal.

## What's here

```
config.py            All settings, from environment variables
database.py           SQLite: items, orders, users, coupons
utils.py               initData verification, TOTP, KHQR generation, delivery text
keep_alive.py          Optional uptime ping (not needed on Railway, kept for compatibility)
webapp_server.py       Flask app — serves both Mini Apps + the full JSON API
store_bot.py            Customer bot — welcome, open app, /myorders, /help
admin_bot.py            Owner bot — /panel, /addcoupon, /broadcast, /stats
main.py                 Runs all three (web + both bots) in one process
requirements.txt
Procfile                For Railway/Heroku-style single-service deploy
.env.example
webapp/templates/index.html   Store Mini App
webapp/templates/admin.html   Admin Mini App
webapp/assets/                style.css, app.js, data.js
media/                         Uploaded photos, videos, QR codes land here
```

## How it fits together

- **Store Bot** → `/start` opens the **Store Mini App** (`webapp/templates/index.html`),
  which does all the actual browsing/buying/order-history work via the API in
  `webapp_server.py`.
- **Admin Bot** → `/panel` opens the **Admin Mini App**, which does item creation,
  order approval, and coupon management. The bot itself only keeps `/addcoupon`,
  `/broadcast`, and `/stats` as chat commands — everything else lives in the panel,
  per your "if it can be in the panel, don't put it in the bot" instruction.
- **`database.py`** is the single source of truth both bots and the web server read
  from — buy through the bot's text flow or the Mini App, it's the same order table.

## Local setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env — at minimum: STORE_BOT_TOKEN, ADMIN_BOT_TOKEN, OWNER_IDS
python main.py
```

Get bot tokens from [@BotFather](https://t.me/BotFather). Get your own Telegram ID
from [@userinfobot](https://t.me/userinfobot) — that goes in `OWNER_IDS`.

The web server starts on `http://localhost:8080`. The bots start polling immediately.
Locally, `WEBAPP_URL` is blank, so the bots' "Open App" button won't render — that's
expected; deploy to get a public HTTPS URL Telegram Mini Apps require.

## Deploying on Railway

1. Push this folder to a GitHub repo.
2. Railway → **New Project → Deploy from GitHub repo**.
3. **Variables** — set everything from `.env.example`:
   ```
   STORE_BOT_TOKEN=...
   ADMIN_BOT_TOKEN=...
   OWNER_IDS=123456789
   WEBAPP_URL=https://your-app.up.railway.app   (set this AFTER step 4)
   DB_PATH=/data/store.db
   MEDIA_DIR=/data/media
   BAKONG_ACCOUNT_ID=...        (optional — see "KHQR" below)
   MERCHANT_NAME=Uchiro Store
   MERCHANT_CITY=Phnom Penh
   BAKONG_API_TOKEN=...          (optional)
   ```
4. **Settings → Networking → Generate Domain**, copy it, and set `WEBAPP_URL` to
   `https://<that-domain>` (with `https://`, no trailing slash). Redeploy.
5. **Settings → Volumes → New Volume**, mount at `/data`. This is what makes
   `DB_PATH=/data/store.db` and `MEDIA_DIR=/data/media` survive redeploys — without
   this, Railway's filesystem resets every deploy and you lose all orders/photos.
6. Railway auto-detects the `Procfile` and runs `python main.py`. One service, both
   bots, the web server, all up together.

### Optional: three separate services instead

If you'd rather scale the bots and web server independently, create three Railway
services from the same repo instead of using the `Procfile`, with these Start Commands:
- `python webapp_server.py` (this one gets the public domain)
- `python store_bot.py`
- `python admin_bot.py`

## KHQR — real auto-payment, with an honest fallback

- Set `BAKONG_ACCOUNT_ID`, `MERCHANT_NAME`, `MERCHANT_CITY` → checkout generates a
  real, scannable KHQR code via the [`bakong-khqr`](https://pypi.org/project/bakong-khqr/)
  package.
- Also set `BAKONG_API_TOKEN` (get one from [Bakong's Open API portal](https://api-bakong.nbc.gov.kh),
  which requires your own registered Bakong merchant account) → `/api/order/<id>/status`
  actually polls Bakong and **auto-approves + delivers the moment that exact bill is
  paid**, no admin action needed.
- Without `BAKONG_API_TOKEN`, the QR still works for payment, but confirmation falls
  back to the buyer uploading a screenshot and an admin approving from the panel or
  bot — still a complete flow, just one manual step.

I can't obtain a Bakong token for you — that requires your own registered merchant
account with the National Bank of Cambodia. Everything else works without it.

## What each requested feature maps to

| You asked for | Where it lives |
|---|---|
| Category filter (All + MM2/Fruit/...) | `webapp/assets/app.js` `renderChips()`, reads `config.CATEGORIES` |
| Small cards, big warranty badge, NEW badge | `webapp/assets/style.css` `.warranty-ribbon`, `.new-badge` |
| Zoom on product photo + QR | `.lightbox` in `style.css` / `openLightbox()` in `app.js` |
| KHQR + 10-min window | `config.ORDER_EXPIRES_MINUTES`, checked in `api_order_status` |
| Auto-delivery w/ conditional authenticator help | `utils.build_delivery_message()` + `has_totp` flag |
| Live code + refresh | `/api/order/<id>/refresh-code` → `utils.generate_totp_code()` |
| Live warranty countdown | `warranty_expires_at` on the order, rendered client-side |
| Coupon at checkout | `database.validate_coupon()` / `redeem_coupon()`, wired into quote+submit |
| Coupon add via bot, view/close in panel | `/addcoupon` in `admin_bot.py`; `/api/admin/coupons` in `webapp_server.py` |
| Account: no stock question, warranty select, optional login/password/authenticator, video | `webapp/templates/admin.html` add-product form + `database.add_item()` |
| Auto-close sold items | `database.decrement_stock()` unpublishes at quantity 0 |
| KH/EN toggle | `I18N` dict in `data.js`, `setLang()` in `app.js` |
| Song on/off | Help tab in `index.html`, needs `media/music.mp3` uploaded |
| Minimal bots, panel does the work | `store_bot.py` (4 commands) / `admin_bot.py` (6 commands) |
| main.py runs everything | `main.py` |

## Known limits, stated plainly

- **PATCH /api/admin/items/<id>** (editing an existing item) returns `501 not implemented` —
  only create/delete are wired up. Add an `update_item()` to `database.py` and fill in
  the route when you need editing.
- **Logo/music**: drop `logo.png` / `music.mp3` into `media/` and they're picked up
  automatically (`webapp_server.py` checks for them on startup).
- **This is new code**, not a copy of a previously existing repo — I wrote it fresh
  based on everything discussed in this conversation. Test it locally first
  (`python main.py`) before pointing real buyers at it, and go through the checkout
  and admin-approve flow end to end at least once.
