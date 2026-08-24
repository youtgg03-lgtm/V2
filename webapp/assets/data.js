/* ============================================================
   Real API wiring for webapp_server.py, plus the small set of
   NEW routes this update needs (marked with ⚠️ NEW — see the
   backend patch notes for the Flask code to add).
   ============================================================ */

function getInitData(){
  return (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData) || '';
}

const API = {
  items: () => fetch('/api/items').then(r => r.json()),

  // ⚠️ NEW: quote now optionally accepts a coupon code and returns the
  // discounted total. See backend patch notes for the updated route.
  quote: (item_id, coupon_code) => fetch('/api/order/quote', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ item_id, coupon_code: coupon_code || undefined, init_data: getInitData() })
  }).then(r => r.json()),

  submit: (item_id, khqr_md5, photoFile, coupon_code) => {
    const form = new FormData();
    form.append('init_data', getInitData());
    form.append('item_id', item_id);
    if(khqr_md5) form.append('khqr_md5', khqr_md5);
    if(coupon_code) form.append('coupon_code', coupon_code); // ⚠️ NEW field
    if(photoFile) form.append('photo', photoFile);
    return fetch('/api/order/submit', { method: 'POST', body: form }).then(r => r.json());
  },

  status: (order_id) => fetch(`/api/order/${order_id}/status?init_data=${encodeURIComponent(getInitData())}`).then(r => r.json()),
  refreshCode: (order_id) => fetch(`/api/order/${order_id}/refresh-code?init_data=${encodeURIComponent(getInitData())}`).then(r => r.json()),
  myOrders: () => fetch(`/api/my-orders?init_data=${encodeURIComponent(getInitData())}`).then(r => r.json()),
  rules: () => fetch('/api/rules').then(r => r.json()),

  // ---- admin ----
  adminVerify: () => fetch('/api/admin/verify', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ init_data: getInitData() })
  }).then(r => r.json()),
  adminItems: () => fetch(`/api/admin/items?init_data=${encodeURIComponent(getInitData())}`).then(r => r.json()),
  adminOrders: () => fetch(`/api/admin/orders?init_data=${encodeURIComponent(getInitData())}`).then(r => r.json()),
  adminCreateItem: (formData) => {
    formData.append('init_data', getInitData());
    return fetch('/api/admin/items', { method: 'POST', body: formData }).then(r => r.json());
  },
  // ⚠️ NEW routes — see backend patch notes
  adminCoupons: () => fetch(`/api/admin/coupons?init_data=${encodeURIComponent(getInitData())}`).then(r => r.json()),
  adminDisableCoupon: (code) => fetch('/api/admin/coupons/disable', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ init_data: getInitData(), code })
  }).then(r => r.json()),
  adminOrderDecision: (order_id, action) => fetch(`/api/admin/orders/${order_id}/${action}`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ init_data: getInitData() })
  }).then(r => r.json()),
};

/* ============================================================
   Category emoji — custom Telegram Premium emoji tags
   ============================================================ */
const CATEGORY_EMOJI = {
  "Account": '<tg-emoji emoji-id="5310070232155436036">👑</tg-emoji>',
  "Fruit": '<tg-emoji emoji-id="6084765169940961891">🍈</tg-emoji>',
  "Gamepass": '<tg-emoji emoji-id="6301052490242597458">🎫</tg-emoji>',
  "Evade": '<tg-emoji emoji-id="5210965493887819972">🏃</tg-emoji>',
  "Robux": '<tg-emoji emoji-id="5202189539967267386">💎</tg-emoji>',
  "Blade Ball": '<tg-emoji emoji-id="5408935401442267103">⚔️</tg-emoji>',
  "MM2": '<tg-emoji emoji-id="5242288969550422350">🔪</tg-emoji>',
};
function categoryEmoji(cat){ return CATEGORY_EMOJI[cat] || '<tg-emoji emoji-id="5854908544712707500">📦</tg-emoji>'; }

/* ============================================================
   KH / EN dictionary — updated with custom Premium emojis
   ============================================================ */
const I18N = {
  en: {
    tab_shop: "Shop", tab_orders: "Orders", tab_help: "Help",
    all: "All", buy_now: "Buy now", sold_out: "Sold out", new: "NEW",
    warranty_days: (d) => `${d}D`, trade: "Trade",
    checkout: "Checkout", total: "Total", upload_screenshot: "Upload payment screenshot",
    no_screenshot: "No screenshot selected yet", submit_order: "Submit order",
    coupon_code: "Coupon code", apply: "Apply",
    waiting: "Waiting for confirmation…", delivered: 'Delivered <tg-emoji emoji-id="5904704361182798355">✅</tg-emoji>', rejected: "Order rejected",
    not_confirmed: "Not confirmed — contact admin", check_my_account: "Check my account",
    back_home: "Back to home", view_orders: "View my orders",
    delivery_details: "Delivery details", live_code: "Live authenticator code", refresh: "Refresh",
    how_to_login: "How to log in with this code", my_orders: "My orders", no_orders: "No orders yet",
    warranty_left: "warranty left", warranty_expired: "Warranty expired",
    help_title: "Help", warranty_policy: "Warranty policy", contact_admin: "Message admin",
    join_channel: "Join channel", song: "Relax music", how_to_login_full: "How to install & log in",
  },
  km: {
    tab_shop: "ទំនិញ", tab_orders: "ការបញ្ជាទិញ", tab_help: "ជំនួយ",
    all: "ទាំងអស់", buy_now: "ទិញឥឡូវ", sold_out: "អស់ស្តុក", new: "ថ្មី",
    warranty_days: (d) => `${d}ថ្ងៃ`, trade: "Trade",
    checkout: "ទូទាត់", total: "សរុប", upload_screenshot: "Upload រូបភាពទូទាត់",
    no_screenshot: "មិនទាន់ជ្រើសរើសរូបភាពទេ", submit_order: "ដាក់ស្នើការបញ្ជាទិញ",
    coupon_code: "លេខកូដបញ្ចុះតម្លៃ", apply: "ប្រើ",
    waiting: "កំពុងរង់ចាំបញ្ជាក់…", delivered: 'ប្រគល់ជូនរួច <tg-emoji emoji-id="5904704361182798355">✅</tg-emoji>', rejected: "Order មិនត្រូវបានអនុម័ត",
    not_confirmed: "មិនទាន់បញ្ជាក់ — ទាក់ទង Admin", check_my_account: "មើលគណនីរបស់ខ្ញុំ",
    back_home: "ត្រឡប់ទៅដើម", view_orders: "មើលការបញ្ជាទិញរបស់ខ្ញុំ",
    delivery_details: "ព័ត៌មានប្រគល់ជូន", live_code: "លេខកូដផ្ទាល់", refresh: "ធ្វើឲ្យស្រស់",
    how_to_login: "របៀបប្រើលេខកូដនេះ", my_orders: "ការបញ្ជាទិញរបស់ខ្ញុំ", no_orders: "មិនទាន់មាន Order ទេ",
    warranty_left: "នៅសល់", warranty_expired: "Warranty ផុតកំណត់",
    help_title: "ជំនួយ", warranty_policy: "វិធាន Warranty", contact_admin: "ទាក់ទងម្ចាស់ហាង",
    join_channel: "ចូល Channel", song: "តន្ត្រី", how_to_login_full: "របៀបដំឡើង និងចូលគណនី",
  }
};
let currentLang = 'km';
function t(key, ...args){
  const val = (I18N[currentLang] && I18N[currentLang][key]) || I18N.en[key] || key;
  return typeof val === 'function' ? val(...args) : val;
}
```[cite: 1, 11]
