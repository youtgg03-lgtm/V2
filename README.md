# Uchiro Store — Frontend Package

This zip is the **frontend layer** for your Uchiro Store ecosystem — it's built to sit
on top of your existing `V3` repo (`store_bot.py`, `admin_bot.py`, `webapp_server.py`,
`database.py`, `config.py`), not replace it. Nothing here talks to a real database yet —
every page uses mock data clearly marked in `assets/data.js`, with comments showing
exactly which of your existing functions each piece should call once wired up.

## What's in the zip

```
uchiro-package/
├── hub.html                    One landing page linking all 5 entry points
│                                (website, Store Bot, Store Mini App,
│                                Admin Bot, Admin Mini App)
│
├── website/                    Standalone multi-page storefront
│   ├── index.html              Homepage
│   ├── products.html           Full catalog, filterable
│   ├── checkout.html           KHQR payment + coupon code
│   ├── orders.html             Order history, live auth code, warranty countdown
│   ├── help.html                Contact, warranty policy, authenticator guide, FAQ
│   ├── login.html              Login / register / forgot password
│   ├── admin.html              Shopify-style admin dashboard (browser version)
│   └── assets/                 style.css, app.js, data.js (mock catalog/orders/coupons)
│
├── webapp/                     Telegram Mini App — copy this INTO your V3 repo's
│   │                           existing webapp/ folder (see "Merging" below)
│   ├── templates/
│   │   ├── index.html          Store Mini App (opens from Store Bot)
│   │   └── admin.html          Admin Mini App (opens from Admin Bot's /panel)
│   └── assets/                 style.css, app.js, data.js (Telegram WebApp SDK wired in)
│
└── admin_bot_additions.py      /broadcast command + page-view tracking —
                                 the two things NOT already in your admin_bot.py.
                                 Everything else (/stats, /users, /addcoupon,
                                 /listcoupons, /release) already exists in your repo
                                 and is untouched.
```

## What's real vs. what's a placeholder — updated after reading your actual code

I read `config.py`, `store_bot.py`, and `webapp_server.py` directly (not just the README),
and rewired `webapp/assets/app.js` + `webapp/templates/*.html` to call your **real** API
instead of mock data. Your backend is further along than the earlier version of this
package assumed:

**Already fully real and wired up:**
- `/api/items`, `/api/order/quote`, `/api/order/submit` (screenshot upload), `/api/order/<id>/status`
  (which actually polls Bakong and auto-approves + delivers on confirmed KHQR payment),
  `/api/order/<id>/refresh-code` (real server-side TOTP), `/api/my-orders`, `/api/rules`
- Admin: `/api/admin/verify`, `/api/admin/items` (GET/POST/PATCH/DELETE), `/api/admin/orders`
- The Mini App templates now use Jinja (`{{ url_for('assets', ...) }}`, `{{ admin_username }}`,
  `{{ channel_username }}`, `{{ categories }}`) to match exactly what `webapp_server.py`'s
  `render_template()` calls already pass in — drop these files in and they should just work.

**Genuinely missing — flagged in the UI, not just comments:**
- **Order approve/reject via API** — `webapp_server.py` has no `/api/admin/orders/<id>/approve`
  route. Only the Admin Bot's inline ✅/❌ buttons can approve orders right now. The admin
  Mini App's Orders tab shows pending orders but says so plainly instead of pretending to have
  a working button.
- **Coupons via the web API** — coupons are fully real (`/addcoupon`, `/listcoupons`,
  `/disablecoupon` in `admin_bot.py`), but bot-only. No `/api/admin/coupons` route exists yet,
  so the admin Mini App's Coupons tab says to use the bot for now instead of faking it.
- **`/broadcast`** — still not in your `admin_bot.py`. `admin_bot_additions.py` in this zip has
  the real code to add it.
- **Dashboard stats** — there's no single `/api/admin/stats` route, so the dashboard numbers
  are computed client-side from `/api/admin/items` + `/api/admin/orders`. User count specifically
  isn't available via the web API at all — use the bot's `/stats` for that until you add one.

## How this maps to your real V3 repo

| This package | Talks to (in your V3 repo) |
|---|---|
| `webapp/templates/index.html` + `webapp/assets/app.js` | Calls the real `/api/items`, `/api/order/quote`, `/api/order/submit`, `/api/order/<id>/status`, `/api/order/<id>/refresh-code`, `/api/my-orders` routes already in `webapp_server.py` — no mock data left |
| `webapp/templates/admin.html` | Calls real `/api/admin/items` and `/api/admin/orders`; Coupons/Broadcast tabs are honest placeholders until those routes exist |
| `website/*.html` | Standalone browser site — still mock data, since it's not part of your Mini App flow. Would need its own routes in `webapp_server.py` if you want it live too |
| `admin_bot_additions.py` | Paste the two new functions into `database.py`, register `broadcast_cmd` in `admin_bot.py`'s `build_app()` |

## Running it locally (preview only, no backend)

You don't need Python for this — it's static HTML/JS. From inside `website/` or
`webapp/templates/`:

```bash
cd website
python3 -m http.server 8000
# open http://localhost:8000
```

This shows you the design and interactions with mock data. Nothing persists and no
real payment happens — that's expected until it's wired to your backend.

---

## Deploying the real thing on Railway

This assumes you're deploying your **actual V3 repo** (which has the bots and
`webapp_server.py`) with the `webapp/` folder from this package merged in. Railway runs
your Python backend; the HTML here is just static files that backend serves.

### 1. Merge the files into your V3 repo

Your `store_bot.py` already builds the Mini App button correctly (`WebAppInfo(url=WEBAPP_URL)`
on `/start` and `/shop`) — nothing to change there. Just drop in the updated templates/assets:

```bash
# from inside your local V3 checkout
cp -r /path/to/uchiro-package/webapp/templates/* webapp/templates/
cp -r /path/to/uchiro-package/webapp/assets/* webapp/assets/
cp /path/to/uchiro-package/admin_bot_additions.py .
# then hand-merge the two functions from admin_bot_additions.py into database.py,
# and register broadcast_cmd inside admin_bot.py's build_app()
git add . && git commit -m "Premium Mini App UI wired to the real API + broadcast command"
git push
```

`webapp_server.py` already serves `/admin` (`admin_page()`), but nothing in `admin_bot.py`
currently opens it — add a `/panel` command there:

```python
from telegram import WebAppInfo
async def panel_cmd(update, context):
    if not db.is_admin_id(update.effective_user.id):
        return await update.message.reply_text("Owner only.")
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(
        "📊 Open Admin Panel", web_app=WebAppInfo(url=f"{WEBAPP_URL}/admin"))]])
    await update.message.reply_text("Tap below to open the dashboard:", reply_markup=kb)
# app.add_handler(CommandHandler("panel", panel_cmd))
```

If you also want the standalone `website/` as a real site (not just the Mini App), it's
still on mock data — see the gaps section below before treating it as production-ready.

### 2. Create the Railway project

1. Go to [railway.app](https://railway.app) → **New Project → Deploy from GitHub repo**.
2. Pick your `V3` repo (or the fork/branch with this package merged in).
3. Railway auto-detects Python via `requirements.txt`. Make sure that file lists
   whatever your bots and `webapp_server.py` need (e.g. `python-telegram-bot`,
   `flask` or `fastapi`, `uvicorn`/`gunicorn`).

### 3. Set environment variables

In Railway → your project → **Variables**, add whatever `config.py` reads from the
environment — at minimum:

```
STORE_BOT_TOKEN=...
ADMIN_BOT_TOKEN=...
OWNER_IDS=123456789,987654321
WEBAPP_URL=https://your-app-name.up.railway.app
KHQR_API_KEY=...
```

Railway sets `PORT` for you automatically — make sure `webapp_server.py` binds to
`0.0.0.0:$PORT`, not a hardcoded port.

### 4. Add a Procfile (or railway.json)

Railway needs to know how to start your process(es). Since you have three long-running
processes (store bot, admin bot, web server), the simplest Railway-native approach is
**three separate services from the same repo**, each with its own start command:

```
# Procfile (if using one service per process type)
web: python webapp_server.py
worker: python store_bot.py
release-worker: python admin_bot.py
```

In Railway, create three services pointing at the same GitHub repo, and set each
service's **Start Command** individually (Settings → Deploy):
- Service 1 (public): `python webapp_server.py`
- Service 2: `python store_bot.py`
- Service 3: `python admin_bot.py`

Only the web server service needs a public domain — Railway → that service →
**Settings → Networking → Generate Domain**. Use that domain as `WEBAPP_URL`.

### 5. Database persistence — important

If `database.py` uses SQLite with a local file (e.g. `store.db`), Railway's default
filesystem is **ephemeral** — it resets on every redeploy. To keep real orders/users/
coupons across deploys:

- Add a **Railway Volume** (Project → your web service → **Settings → Volumes → New
  Volume**), mount it at e.g. `/data`, and point `database.py`'s `DB_PATH` at
  `/data/store.db` via an environment variable.
- Or migrate to Railway's managed **PostgreSQL** plugin for a proper hosted database —
  more work up front, but avoids the single-writer limits of SQLite once you have
  concurrent bot + web traffic.

### 6. Point your bots' WebApp buttons at the live URL

Once deployed, update wherever `store_bot.py` / `admin_bot.py` build the
`WebAppInfo(url=...)` for the menu button to use your Railway domain:

```python
WebAppInfo(url=f"{WEBAPP_URL}/")        # Store Mini App
WebAppInfo(url=f"{WEBAPP_URL}/admin")   # Admin Mini App
```

### 7. Test the loop end to end

1. Open the Store Bot in Telegram → tap the Mini App button → confirm it loads on
   your Railway domain, not `localhost`.
2. Place a test order → confirm it appears in `orders.html` / the Admin Mini App's
   Orders tab.
3. Run `/broadcast test message` in the Admin Bot → confirm your test account
   receives it via the Store Bot.

---

## Known gaps to close before going live

These are flagged inline in the code with comments, but the short list:

- **KHQR payment** — checkout pages show a placeholder QR and a "simulate payment"
  button. Replace with a real call to your KHQR provider's API, and have it hit a
  webhook route in `webapp_server.py` that calls your existing order-approval logic.
- **Live authenticator codes** — `orders.html` / the Orders tab show a demo 6-digit
  ticker, not a real TOTP. Generate the real code server-side (e.g. `pyotp.TOTP(secret).now()`)
  from the encrypted secret stored per order, and only serve it to that order's
  authenticated owner.
- **Login / session** — the login/register/forgot-password forms are UI only. Wire to
  real `/api/login`, `/api/register`, `/api/forgot-password` routes with hashed
  passwords and session cookies (or JWT).
- **`hub.html`'s live activity feed** — this uses Claude's artifact storage API, which
  only works inside Claude.ai. Once deployed on Railway, replace it with a small
  `/api/activity` endpoint backed by your real database instead.
