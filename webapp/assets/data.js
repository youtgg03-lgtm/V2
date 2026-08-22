/* ============================================================
   Real API wiring for webapp_server.py.
   No more mock CATALOG/ORDERS — every value here now comes from
   a real fetch() to your Flask app, using the exact field names
   webapp_server.py actually returns.
   ============================================================ */

// Telegram initData, sent as `init_data` to every authenticated call —
// this is what verify_webapp_init_data() in utils.py checks server-side.
function getInitData(){
  return (window.Telegram && window.Telegram.WebApp && window.Telegram.WebApp.initData) || '';
}

const API = {
  items: () => fetch('/api/items').then(r => r.json()),

  quote: (item_id) => fetch('/api/order/quote', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ item_id })
  }).then(r => r.json()),

  // webapp_server.py's /api/order/submit expects multipart form data:
  // init_data, item_id, khqr_md5 (from quote, if KHQR was shown), and photo (payment screenshot).
  submit: (item_id, khqr_md5, photoFile) => {
    const form = new FormData();
    form.append('init_data', getInitData());
    form.append('item_id', item_id);
    if(khqr_md5) form.append('khqr_md5', khqr_md5);
    if(photoFile) form.append('photo', photoFile);
    return fetch('/api/order/submit', { method: 'POST', body: form }).then(r => r.json());
  },

  status: (order_id) => fetch(`/api/order/${order_id}/status?init_data=${encodeURIComponent(getInitData())}`).then(r => r.json()),

  refreshCode: (order_id) => fetch(`/api/order/${order_id}/refresh-code?init_data=${encodeURIComponent(getInitData())}`).then(r => r.json()),

  myOrders: () => fetch(`/api/my-orders?init_data=${encodeURIComponent(getInitData())}`).then(r => r.json()),

  rules: () => fetch('/api/rules').then(r => r.json()),

  // ---- admin API (webapp/templates/admin.html) ----
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
};

