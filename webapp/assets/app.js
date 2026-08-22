/* ============================================================
   UCHIRO STORE — Telegram Mini App logic
   Wired to the REAL webapp_server.py API (see assets/data.js's
   API object). No mock data — everything below is a live fetch.
   ============================================================ */

const tg = window.Telegram ? window.Telegram.WebApp : null;
let itemsById = {};

/* ---------- 1. Telegram WebApp bootstrap ---------- */
function initTelegram(){
  if(!tg){
    document.getElementById('tg-user').textContent = 'preview mode (open via bot to test live)';
    return;
  }
  tg.ready();
  tg.expand();
  applyTelegramTheme();
  tg.onEvent('themeChanged', applyTelegramTheme);
  const user = tg.initDataUnsafe && tg.initDataUnsafe.user;
  document.getElementById('tg-user').textContent = user ? ('@' + (user.username || user.first_name)) : 'guest';
  tg.BackButton.onClick(closeSheet);
}

function applyTelegramTheme(){
  if(!tg || !tg.themeParams) return;
  const p = tg.themeParams;
  const root = document.documentElement.style;
  if(p.bg_color) root.setProperty('--void', p.bg_color);
  if(p.secondary_bg_color) root.setProperty('--surface', p.secondary_bg_color);
  if(p.text_color) root.setProperty('--ivory', p.text_color);
  if(p.hint_color) root.setProperty('--slate', p.hint_color);
  if(tg.setHeaderColor) tg.setHeaderColor('secondary_bg_color');
  if(tg.setBackgroundColor) tg.setBackgroundColor(p.bg_color || '#0a0b0e');
}
function haptic(type){ if(tg && tg.HapticFeedback) tg.HapticFeedback.impactOccurred(type || 'light'); }
function notify(type){ if(tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred(type); }

/* ---------- 2. Tab navigation ---------- */
function switchTab(tab){
  document.querySelectorAll('.screen').forEach(s => s.classList.add('hidden'));
  document.getElementById('screen-' + tab).classList.remove('hidden');
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  haptic('light');
  if(tab === 'orders') loadOrders();
  window.scrollTo(0,0);
}

/* ---------- 3. Catalog — GET /api/items ---------- */
let activeCategory = 'all';
let allCategories = [];

function pcardHTML(item){
  const isAccount = item.category === 'Account';
  const badge = isAccount
    ? `<span class="badge badge-account">🛡️ ${item.warranty_days || 0}d</span>`
    : `<span class="badge badge-trade">🔄 ${item.quantity} left</span>`;
  const media = item.photo_url ? `<img src="${item.photo_url}" style="width:100%; height:100%; object-fit:cover; border-radius:14px 14px 0 0;">` : item.category;
  return `
    <div class="pcard" onclick="openProduct(${item.id})">
      <div class="pcard-media">${badge}${item.is_new ? '<span class="badge" style="right:8px; left:auto; background:rgba(255,92,92,.18); color:var(--ember);">NEW</span>' : ''}${media}</div>
      <div class="pcard-body">
        <h3>${item.name}</h3>
        <div class="pcard-foot">
          <span class="price">$${item.price}</span>
          <span class="stock">${isAccount ? 'x1' : 'x' + item.quantity}</span>
        </div>
      </div>
    </div>`;
}

function renderCatalog(items){
  itemsById = Object.fromEntries(items.map(i => [i.id, i]));
  const grid = document.getElementById('product-grid');
  const filtered = items.filter(i => activeCategory === 'all' || i.category === activeCategory);
  grid.innerHTML = filtered.length ? filtered.map(pcardHTML).join('') :
    `<div class="empty-state" style="grid-column:1/-1;">Nothing here yet — check back soon.</div>`;
}

function renderChips(){
  const row = document.getElementById('chip-row');
  const cats = ['all', ...allCategories];
  row.innerHTML = cats.map(c => `<button class="chip ${c===activeCategory?'active':''}" onclick="setCategory('${c}')">${c==='all'?'All':c}</button>`).join('');
}
function setCategory(c){
  activeCategory = c;
  renderChips();
  renderCatalog(Object.values(itemsById));
  haptic('light');
}

async function loadCatalog(){
  document.getElementById('product-grid').innerHTML = `<div class="empty-state" style="grid-column:1/-1;">Loading catalog…</div>`;
  try{
    const data = await API.items(); // { items: [...], categories: [...] }
    allCategories = data.categories || [];
    renderChips();
    renderCatalog(data.items || []);
  }catch(e){
    document.getElementById('product-grid').innerHTML = `<div class="empty-state" style="grid-column:1/-1;">Couldn't load the catalog. Pull to refresh or check your connection.</div>`;
  }
}

/* ---------- 4. Product detail sheet ---------- */
let currentItem = null;

function openSheet(id){
  document.getElementById(id).classList.add('open');
  document.getElementById('backdrop').classList.add('open');
  if(tg) tg.BackButton.show();
}
function closeSheet(){
  document.querySelectorAll('.sheet.open').forEach(s => s.classList.remove('open'));
  document.getElementById('backdrop').classList.remove('open');
  if(tg){ tg.BackButton.hide(); tg.MainButton.hide(); }
}

function openProduct(id){
  currentItem = itemsById[id];
  if(!currentItem) return;
  const isAccount = currentItem.category === 'Account';
  document.getElementById('product-sheet-body').innerHTML = `
    <div class="sheet-media">${currentItem.photo_url ? `<img src="${currentItem.photo_url}" style="width:100%; height:100%; object-fit:cover; border-radius:12px;">` : currentItem.category}</div>
    <h2>${currentItem.name}</h2>
    <div class="desc">${currentItem.description || ''}</div>
    <div class="tag-row">
      <span class="tag">${currentItem.category}</span>
      ${isAccount ? `<span class="tag">🛡️ ${currentItem.warranty_days}-day warranty</span>` : `<span class="tag">${currentItem.quantity} in stock</span>`}
    </div>
    <div class="row-between">
      <span class="mono" style="font-size:22px; font-weight:700;">$${currentItem.price}</span>
      <span class="muted" style="font-size:12px;">Delivered ${isAccount ? 'to your order history' : 'in-game, ~10 min'}</span>
    </div>
  `;
  openSheet('product-sheet');
  if(tg){
    tg.MainButton.setText('Buy now — $' + currentItem.price);
    tg.MainButton.show();
    tg.MainButton.offClick(goToCheckout);
    tg.MainButton.onClick(goToCheckout);
  }
  haptic('medium');
}

/* ---------- 5. Checkout — POST /api/order/quote, then /api/order/submit ---------- */
let currentQuote = null;
let selectedPhotoFile = null;

async function goToCheckout(){
  closeSheet();
  selectedPhotoFile = null;
  openSheet('checkout-sheet');
  document.getElementById('checkout-item-name').textContent = currentItem.name;
  document.getElementById('checkout-total').textContent = '$' + currentItem.price;
  document.getElementById('checkout-qr').innerHTML = `<div class="qr-inner">Loading QR…</div>`;
  document.getElementById('checkout-photo-status').textContent = 'No screenshot selected yet';
  document.getElementById('checkout-pending').classList.remove('hidden');
  document.getElementById('checkout-waiting').classList.add('hidden');
  document.getElementById('checkout-rejected').classList.add('hidden');
  document.getElementById('checkout-success').classList.add('hidden');
  if(tg){ tg.MainButton.hide(); }

  try{
    currentQuote = await API.quote(currentItem.id); // { qr_url, khqr_md5, note, ... }
    document.getElementById('checkout-qr').innerHTML = currentQuote.qr_url
      ? `<img src="${currentQuote.qr_url}" style="width:100%; height:100%; object-fit:contain; border-radius:8px;">`
      : `<div class="qr-inner">QR not set up yet — contact the admin to pay directly.</div>`;
    document.getElementById('checkout-note').textContent = currentQuote.note || '';
  }catch(e){
    document.getElementById('checkout-qr').innerHTML = `<div class="qr-inner">Couldn't load payment QR. Try again.</div>`;
  }
}

function onScreenshotPicked(input){
  selectedPhotoFile = input.files && input.files[0];
  document.getElementById('checkout-photo-status').textContent = selectedPhotoFile
    ? `Selected: ${selectedPhotoFile.name}` : 'No screenshot selected yet';
}

async function submitOrder(){
  if(!selectedPhotoFile){
    notify('error');
    document.getElementById('checkout-photo-status').style.color = 'var(--ember)';
    return;
  }
  const btn = document.getElementById('submit-order-btn');
  btn.disabled = true; btn.textContent = 'Submitting…';
  try{
    const res = await API.submit(currentItem.id, currentQuote && currentQuote.khqr_md5, selectedPhotoFile);
    if(res.error){
      btn.disabled = false; btn.textContent = 'Submit order';
      notify('error');
      alert('Could not submit: ' + res.error);
      return;
    }
    notify('success'); haptic('heavy');
    pollOrderStatus(res.order_id);
  }catch(e){
    btn.disabled = false; btn.textContent = 'Submit order';
    notify('error');
  }
}

let pollTimer = null;
function pollOrderStatus(orderId){
  document.getElementById('checkout-pending').classList.add('hidden');
  document.getElementById('checkout-waiting').classList.remove('hidden');
  document.getElementById('checkout-waiting-order-id').textContent = '#' + orderId;

  clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    // /api/order/<id>/status also triggers the real Bakong check server-side —
    // if it's paid, this call itself flips it to approved and returns delivery info.
    const status = await API.status(orderId);
    if(status.status === 'approved'){
      clearInterval(pollTimer);
      showDelivery(orderId, status);
    }else if(status.status === 'rejected'){
      clearInterval(pollTimer);
      document.getElementById('checkout-waiting').classList.add('hidden');
      document.getElementById('checkout-rejected').classList.remove('hidden');
    }
  }, 4000);
}

function showDelivery(orderId, status){
  document.getElementById('checkout-waiting').classList.add('hidden');
  document.getElementById('checkout-success').classList.remove('hidden');
  document.getElementById('delivery-text').textContent = status.delivery_info || '';
  document.getElementById('delivery-has-totp').classList.toggle('hidden', !status.has_totp);
  if(status.has_totp) wireLiveCode(orderId, 'delivery-code-box');
  notify('success'); haptic('heavy');
}

function finishCheckout(){
  closeSheet();
  switchTab('orders');
}

/* ---------- 6. Orders tab — GET /api/my-orders ---------- */
async function loadOrders(){
  const mount = document.getElementById('orders-list');
  mount.innerHTML = `<div class="empty-state">Loading…</div>`;
  try{
    const data = await API.myOrders(); // { orders: [{id, item_name, status, created_at, warranty}] }
    const orders = data.orders || [];
    if(orders.length === 0){
      mount.innerHTML = `<div class="empty-state">No orders yet — head to the Shop tab.</div>`;
      return;
    }
    mount.innerHTML = orders.map(orderCardHTML).join('');
  }catch(e){
    mount.innerHTML = `<div class="empty-state">Couldn't load your orders. Open this from the Store Bot to sign in automatically.</div>`;
  }
}

function statusPill(status){
  const map = {
    pending:  `<span class="pill"><span class="status-dot status-warn"></span>Pending</span>`,
    approved: `<span class="pill"><span class="status-dot status-live"></span>Delivered</span>`,
    rejected: `<span class="pill"><span class="status-dot status-expired"></span>Rejected</span>`,
  };
  return map[status] || `<span class="pill">${status}</span>`;
}

function orderCardHTML(o){
  const date = new Date(o.created_at).toLocaleDateString(undefined, {month:'short', day:'numeric'});
  return `
    <div class="order-card">
      <div class="row-between">
        <div>
          <div class="mono muted" style="font-size:11px;">#${o.id} · ${date}</div>
          <div style="font-weight:600; font-size:13.5px; margin-top:3px;">${o.item_name}</div>
        </div>
        <div style="text-align:right;">
          ${statusPill(o.status)}
          ${o.warranty ? `<div class="muted mono" style="font-size:10.5px; margin-top:6px;">${o.warranty}</div>` : ''}
        </div>
      </div>
      ${o.status === 'approved' ? `<button class="copy-btn mt-8" style="width:100%; padding:8px; margin-top:10px;" onclick="viewOrderDetail(${o.id})">View delivery details</button>` : ''}
    </div>`;
}

async function viewOrderDetail(orderId){
  const status = await API.status(orderId);
  if(status.status !== 'approved') return;
  openSheet('checkout-sheet');
  document.getElementById('checkout-pending').classList.add('hidden');
  document.getElementById('checkout-waiting').classList.add('hidden');
  document.getElementById('checkout-rejected').classList.add('hidden');
  document.getElementById('checkout-success').classList.remove('hidden');
  document.getElementById('checkout-item-name').textContent = status.item_name || '';
  document.getElementById('delivery-text').textContent = status.delivery_info || '';
  document.getElementById('delivery-has-totp').classList.toggle('hidden', !status.has_totp);
  if(status.has_totp) wireLiveCode(orderId, 'delivery-code-box');
}

/* ---------- live TOTP — GET /api/order/<id>/refresh-code (real, server-generated) ---------- */
async function wireLiveCode(orderId, boxId){
  const box = document.getElementById(boxId);
  async function refresh(){
    box.querySelector('.code').textContent = '…';
    try{
      const res = await API.refreshCode(orderId);
      if(res.code) box.querySelector('.code').textContent = res.code.slice(0,3) + ' ' + res.code.slice(3);
    }catch(e){ /* leave as-is */ }
  }
  box.querySelector('.refresh-btn').onclick = refresh;
  refresh();
}

/* ---------- 7. init ---------- */
document.addEventListener('DOMContentLoaded', () => {
  initTelegram();
  loadCatalog();
  switchTab('shop');
});
