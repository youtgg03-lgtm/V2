/* ============================================================
   UCHIRO STORE — Telegram Mini App logic (real API only)
   ============================================================ */

const tg = window.Telegram ? window.Telegram.WebApp : null;
let itemsById = {};

/* ---------- Telegram bootstrap ---------- */
function initTelegram(){
  if(!tg){
    const el = document.getElementById('tg-user');
    if(el) el.textContent = 'preview';
    return;
  }
  tg.ready(); tg.expand();
  applyTelegramTheme();
  tg.onEvent('themeChanged', applyTelegramTheme);
  tg.BackButton.onClick(closeSheet);
}
function applyTelegramTheme(){
  if(!tg || !tg.themeParams) return;
  const p = tg.themeParams, root = document.documentElement.style;
  if(p.bg_color) root.setProperty('--void', p.bg_color);
  if(p.secondary_bg_color) root.setProperty('--surface', p.secondary_bg_color);
  if(p.text_color) root.setProperty('--ivory', p.text_color);
  if(p.hint_color) root.setProperty('--slate', p.hint_color);
  if(tg.setHeaderColor) tg.setHeaderColor('secondary_bg_color');
  if(tg.setBackgroundColor) tg.setBackgroundColor(p.bg_color || '#0a0b0e');
}
function haptic(type){ if(tg && tg.HapticFeedback) tg.HapticFeedback.impactOccurred(type || 'light'); }
function notify(type){ if(tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred(type); }

/* ---------- language toggle ---------- */
function setLang(lang){
  currentLang = lang;
  document.getElementById('lang-label').textContent = lang.toUpperCase();
  renderChips();
  renderCollections(Object.values(itemsById));
  renderCatalog(Object.values(itemsById));
  document.querySelectorAll('[data-i18n]').forEach(el => el.textContent = t(el.dataset.i18n));
  document.querySelectorAll('.tab-btn').forEach(b => {
    const label = { shop: 'tab_shop', orders: 'tab_orders', help: 'tab_help' }[b.dataset.tab];
    if(label) b.querySelector('.label').textContent = t(label);
  });
}
function toggleLang(){ setLang(currentLang === 'km' ? 'en' : 'km'); haptic('light'); }

/* ---------- tabs ---------- */
function switchTab(tab){
  document.querySelectorAll('.screen').forEach(s => s.classList.add('hidden'));
  document.getElementById('screen-' + tab).classList.remove('hidden');
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
  haptic('light');
  if(tab === 'orders') loadOrders();
  window.scrollTo(0,0);
}

/* ---------- zoom lightbox ---------- */
function openLightbox(src){
  document.getElementById('lightbox-img').src = src;
  document.getElementById('lightbox').classList.add('open');
  haptic('light');
}
function closeLightbox(){ document.getElementById('lightbox').classList.remove('open'); }

/* ---------- catalog ---------- */
let activeCategory = 'all';
let allCategories = [];

function pcardHTML(item){
  const isAccount = item.category === 'Account';
  const soldOut = item.quantity <= 0;
  const media = item.photo_url
    ? `<img src="${item.photo_url}" style="width:100%; height:100%; object-fit:cover; border-radius:14px 14px 0 0;">`
    : item.category;
  return `
    <div class="pcard ${soldOut ? 'sold-out' : ''}">
      <div class="pcard-media" onclick="${item.photo_url ? `openLightbox('${item.photo_url}')` : `openProduct(${item.id})`}">
        ${isAccount ? `<div class="warranty-ribbon">🛡️${t('warranty_days', item.warranty_days || 14)}</div>` : `<div class="trade-badge">🔄 ${t('trade')}</div>`}
        ${item.is_new ? `<div class="new-badge">${t('new')}</div>` : ''}
        ${soldOut ? `<div class="sold-badge">${t('sold_out')}</div>` : ''}
        ${media}
      </div>
      <div class="pcard-body">
        <h3 onclick="openProduct(${item.id})">${item.name}</h3>
        <div class="pcard-foot">
          <span class="price">$${item.price}</span>
          <span class="stock">${isAccount ? '' : 'x' + item.quantity}</span>
        </div>
        <button class="buy-btn" onclick="openProduct(${item.id})" ${soldOut ? 'disabled' : ''}>${soldOut ? t('sold_out') : t('buy_now')}</button>
      </div>
    </div>`;
}

function renderCatalog(items){
  itemsById = Object.fromEntries(items.map(i => [i.id, i]));
  const grid = document.getElementById('product-grid');
  // sold-out items with quantity <= 0 are filtered out entirely (auto-close), not just greyed —
  // keeping the sold-out CSS above as a safety net for a brief in-between state.
  const filtered = items.filter(i => i.quantity > 0 && (activeCategory === 'all' || i.category === activeCategory));
  grid.innerHTML = filtered.length ? filtered.map(pcardHTML).join('') :
    `<div class="empty-state" style="grid-column:1/-1;">—</div>`;
}
function renderChips(){
  const row = document.getElementById('chip-row');
  const cats = ['all', ...allCategories];
  row.innerHTML = cats.map(c => `<button class="chip ${c===activeCategory?'active':''}" onclick="setCategory('${c}')">${c==='all'?t('all'):c}</button>`).join('');
}

/* Premium "collection" tiles — tap Account/Fruit/MM2/... to filter, tap
   again (or "All") to see everything mixed while scrolling. Emoji come
   from CATEGORY_EMOJI in data.js — swap those for Premium emoji anytime. */
function renderCollections(items){
  const grid = document.getElementById('collection-grid');
  const counts = {};
  items.forEach(i => { if(i.quantity > 0) counts[i.category] = (counts[i.category] || 0) + 1; });
  const tiles = ['all', ...allCategories].map(c => {
    const label = c === 'all' ? t('all') : c;
    const emoji = c === 'all' ? '🗂️' : categoryEmoji(c);
    const count = c === 'all' ? items.filter(i=>i.quantity>0).length : (counts[c] || 0);
    return `
      <button class="collection-tile ${c===activeCategory?'active':''}" onclick="setCategory('${c}')">
        <span class="emoji">${emoji}</span>
        <span class="label">${label}</span>
        <span class="count">${count}</span>
      </button>`;
  }).join('');
  grid.innerHTML = tiles;
}

function setCategory(c){
  activeCategory = c;
  renderChips();
  renderCollections(Object.values(itemsById));
  renderCatalog(Object.values(itemsById));
  haptic('light');
  document.getElementById('product-grid').scrollIntoView({behavior:'smooth', block:'start'});
}

async function loadCatalog(){
  try{
    const data = await API.items();
    allCategories = data.categories || [];
    itemsById = Object.fromEntries((data.items||[]).map(i => [i.id, i]));
    renderChips();
    renderCollections(data.items || []);
    renderCatalog(data.items || []);
  }catch(e){
    document.getElementById('product-grid').innerHTML = `<div class="empty-state" style="grid-column:1/-1;">…</div>`;
  }
}

/* ---------- product detail sheet ---------- */
let currentItem = null;

function openSheet(id){ document.getElementById(id).classList.add('open'); document.getElementById('backdrop').classList.add('open'); if(tg) tg.BackButton.show(); }
function closeSheet(){ document.querySelectorAll('.sheet.open').forEach(s => s.classList.remove('open')); document.getElementById('backdrop').classList.remove('open'); if(tg){ tg.BackButton.hide(); tg.MainButton.hide(); } }

function openProduct(id){
  currentItem = itemsById[id];
  if(!currentItem) return;
  const isAccount = currentItem.category === 'Account';
  document.getElementById('product-sheet-body').innerHTML = `
    <div class="sheet-media ${currentItem.photo_url ? 'zoomable' : ''}" ${currentItem.photo_url ? `onclick="openLightbox('${currentItem.photo_url}')"` : ''}>
      ${currentItem.photo_url ? `<img src="${currentItem.photo_url}">` : currentItem.category}
    </div>
    <h2>${currentItem.name}</h2>
    <div class="desc">${currentItem.description || ''}</div>
    <div class="tag-row">
      <span class="tag">${currentItem.category}</span>
      ${isAccount ? `<span class="tag tag-warranty">🛡️ ${t('warranty_days', currentItem.warranty_days)}</span>` : `<span class="tag">${currentItem.quantity} left</span>`}
    </div>
    <div class="row-between"><span class="mono" style="font-size:22px; font-weight:700;">$${currentItem.price}</span></div>
  `;
  openSheet('product-sheet');
  if(tg){
    tg.MainButton.setText(t('buy_now') + ' — $' + currentItem.price);
    tg.MainButton.show();
    tg.MainButton.offClick(goToCheckout);
    tg.MainButton.onClick(goToCheckout);
  }
  haptic('medium');
}

/* ---------- checkout ---------- */
let currentQuote = null;
let selectedPhotoFile = null;
let appliedCouponCode = null;

async function goToCheckout(){
  closeSheet();
  selectedPhotoFile = null; appliedCouponCode = null;
  document.getElementById('coupon-input').value = '';
  document.getElementById('coupon-msg').textContent = '';
  openSheet('checkout-sheet');
  showCheckoutStage('pending');
  document.getElementById('checkout-item-name').textContent = currentItem.name;
  document.getElementById('checkout-qr').innerHTML = `<div class="qr-inner">…</div>`;
  document.getElementById('checkout-photo-status').textContent = t('no_screenshot');
  if(tg) tg.MainButton.hide();
  await refreshQuote();
}

async function refreshQuote(){
  try{
    currentQuote = await API.quote(currentItem.id, appliedCouponCode);
    const total = currentQuote.total != null ? currentQuote.total : currentItem.price;
    document.getElementById('checkout-total').textContent = '$' + total;
    document.getElementById('checkout-qr').innerHTML = currentQuote.qr_url
      ? `<img src="${currentQuote.qr_url}" onclick="openLightbox('${currentQuote.qr_url}')" class="zoomable" style="cursor:zoom-in;">`
      : `<div class="qr-inner">QR not set up — contact admin</div>`;
  }catch(e){
    document.getElementById('checkout-qr').innerHTML = `<div class="qr-inner">Couldn't load QR</div>`;
  }
}

async function applyCoupon(){
  const code = document.getElementById('coupon-input').value.trim().toUpperCase();
  if(!code) return;
  appliedCouponCode = code;
  const msg = document.getElementById('coupon-msg');
  await refreshQuote();
  if(currentQuote && currentQuote.coupon_valid === false){
    msg.textContent = currentQuote.coupon_error || 'Invalid code';
    msg.style.color = 'var(--crimson)';
    appliedCouponCode = null;
    notify('error');
  }else if(currentQuote && currentQuote.discount_applied){
    msg.textContent = '✅ ' + currentQuote.discount_applied;
    msg.style.color = 'var(--mint)';
    notify('success');
  }
}

function onScreenshotPicked(input){
  selectedPhotoFile = input.files && input.files[0];
  document.getElementById('checkout-photo-status').textContent = selectedPhotoFile ? selectedPhotoFile.name : t('no_screenshot');
}

function showCheckoutStage(stage){
  ['pending','waiting','rejected','success'].forEach(s =>
    document.getElementById('checkout-' + s).classList.toggle('hidden', s !== stage));
}

async function submitOrder(){
  if(!selectedPhotoFile){
    notify('error');
    document.getElementById('checkout-photo-status').style.color = 'var(--crimson)';
    return;
  }
  const btn = document.getElementById('submit-order-btn');
  btn.disabled = true; btn.textContent = '…';
  try{
    const res = await API.submit(currentItem.id, currentQuote && currentQuote.khqr_md5, selectedPhotoFile, appliedCouponCode);
    if(res.error){ btn.disabled = false; btn.textContent = t('submit_order'); notify('error'); alert(res.error); return; }
    notify('success'); haptic('heavy');
    pollOrderStatus(res.order_id);
  }catch(e){ btn.disabled = false; btn.textContent = t('submit_order'); notify('error'); }
}

let pollTimer = null;
function pollOrderStatus(orderId){
  showCheckoutStage('waiting');
  document.getElementById('checkout-waiting-order-id').textContent = '#' + orderId;
  clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    const status = await API.status(orderId);
    if(status.status === 'approved'){ clearInterval(pollTimer); showDelivery(orderId, status); }
    else if(status.status === 'rejected'){ clearInterval(pollTimer); showCheckoutStage('rejected'); }
  }, 4000);
}

function showDelivery(orderId, status){
  showCheckoutStage('success');
  document.getElementById('checkout-item-name-2').textContent = status.item_name || '';
  document.getElementById('delivery-blocks').innerHTML = deliveryBlocksHTML(orderId, status.fields);
  notify('success'); haptic('heavy');
}

function backToHome(){ closeSheet(); switchTab('shop'); }
function goToMyOrders(){ closeSheet(); switchTab('orders'); }

/* ---------- orders tab ---------- */
async function loadOrders(){
  const mount = document.getElementById('orders-list');
  mount.innerHTML = `<div class="empty-state">…</div>`;
  try{
    const data = await API.myOrders();
    const orders = data.orders || [];
    if(orders.length === 0){ mount.innerHTML = `<div class="empty-state">${t('no_orders')}</div>`; return; }
    mount.innerHTML = orders.map(orderCardHTML).join('');
  }catch(e){
    mount.innerHTML = `<div class="empty-state">…</div>`;
  }
}

function warrantyCountdownHTML(o){
  if(!o.warranty_expires_at) return '';
  const remaining = new Date(o.warranty_expires_at).getTime() - Date.now();
  if(remaining <= 0) return `<div class="warranty-countdown expired"><div class="big">${t('warranty_expired')}</div></div>`;
  const days = Math.floor(remaining/864e5), hours = Math.floor((remaining%864e5)/36e5);
  return `<div class="warranty-countdown"><div class="big">${days}d ${hours}h</div><div class="muted mono" style="font-size:10px;">${t('warranty_left')}</div></div>`;
}

function orderCardHTML(o){
  const date = new Date(o.created_at).toLocaleDateString(undefined, {month:'short', day:'numeric'});
  let statusBadge;
  if(o.status === 'approved') statusBadge = `<span class="pill"><span class="status-dot status-live"></span>${t('delivered')}</span>`;
  else if(o.status === 'rejected') statusBadge = `<span class="pill"><span class="status-dot status-expired"></span>${t('rejected')}</span>`;
  else if(o.is_stale) statusBadge = `<span class="pill"><span class="status-dot status-expired"></span>${t('not_confirmed')}</span>`;
  else statusBadge = `<span class="pill"><span class="status-dot status-warn"></span>${t('waiting')}</span>`;

  return `
    <div class="order-card" id="order-${o.id}">
      <div class="row-between">
        <div><div class="mono muted" style="font-size:11px;">#${o.id} · ${date}</div>
          <div style="font-weight:600; font-size:13.5px; margin-top:3px;">${o.item_name}</div></div>
        <div>${statusBadge}</div>
      </div>
      ${o.status === 'approved' ? `<button class="btn-primary mt-8" style="margin-top:10px;" onclick="toggleCheckAccount(${o.id})" id="check-btn-${o.id}">🔓 ${t('check_my_account')}</button>` : ''}
      ${o.is_stale ? `<a href="https://t.me/${window.ADMIN_USERNAME || ''}" target="_blank" class="btn-secondary mt-8" style="display:block; text-align:center; margin-top:10px;">👤 ${t('contact_admin')}</a>` : ''}
      <div id="order-detail-${o.id}" class="hidden"></div>
    </div>`;
}

async function toggleCheckAccount(orderId){
  const box = document.getElementById('order-detail-' + orderId);
  const btn = document.getElementById('check-btn-' + orderId);
  if(!box.classList.contains('hidden')){ box.classList.add('hidden'); return; }
  box.classList.remove('hidden');
  if(!box.dataset.loaded){
    btn.textContent = '…';
    const status = await API.status(orderId);
    hydrateOrderCard({ id: orderId, ...status });
    box.dataset.loaded = '1';
    btn.textContent = '🔓 ' + t('check_my_account');
  }
  haptic('medium');
}

async function hydrateOrderCard(o){
  const status = o.delivery_info !== undefined ? o : await API.status(o.id);
  const box = document.getElementById('order-detail-' + o.id);
  if(!box || status.status !== 'approved') return;
  box.innerHTML = `
    ${warrantyCountdownHTML(status)}
    <div class="mt-8" style="margin-top:10px;">${deliveryBlocksHTML(o.id, status.fields)}</div>
  `;
}

/* ---------- tap-to-copy field component ---------- */
let copyFieldSeq = 0;
function copyFieldHTML(label, value, opts = {}){
  const id = 'cf-' + (opts.id || (copyFieldSeq++));
  const cls = opts.big ? 'cf-value big-code' : 'cf-value';
  return `
    <div class="copy-field" id="${id}" onclick="copyField('${id}', this)">
      <div class="cf-label"><span>${label}</span><span class="cf-icon">📋</span></div>
      <div class="${cls}" data-raw="${(value||'').replace(/"/g,'&quot;')}">${value || '—'}</div>
      ${opts.refreshable ? `<button class="cf-refresh" onclick="event.stopPropagation(); refreshLiveField('${id}', ${opts.orderId})">${t('refresh')}</button>` : ''}
    </div>`;
}
function copyField(fieldId, el){
  const valueEl = el.querySelector('.cf-value');
  const text = valueEl ? valueEl.dataset.raw : '';
  if(!text || text === '—') return;
  navigator.clipboard.writeText(text);
  el.classList.add('copied');
  setTimeout(() => el.classList.remove('copied'), 900);
  showCopyToast();
  haptic('light');
}
function showCopyToast(){
  let toast = document.getElementById('copy-toast');
  if(!toast){
    toast = document.createElement('div');
    toast.id = 'copy-toast';
    toast.className = 'copy-toast';
    toast.textContent = currentLang === 'km' ? '✅ បានចម្លង!' : '✅ Copied!';
    document.body.appendChild(toast);
  }
  toast.classList.add('show');
  clearTimeout(toast._hideTimer);
  toast._hideTimer = setTimeout(() => toast.classList.remove('show'), 1200);
}
async function refreshLiveField(fieldId, orderId){
  const el = document.getElementById(fieldId);
  const valueEl = el.querySelector('.cf-value');
  valueEl.textContent = '…';
  try{
    const res = await API.refreshCode(orderId);
    if(res.code){
      valueEl.textContent = res.code.slice(0,3) + ' ' + res.code.slice(3);
      valueEl.dataset.raw = res.code;
    }
  }catch(e){}
  haptic('light');
}

/* Builds the full 5-block delivery layout: Name, Password, Setup Key,
   fast-copy Live code (with refresh), and a link to the install guide. */
function deliveryBlocksHTML(orderId, fields){
  if(!fields) return '';
  let html = '';
  if(fields.login_name) html += copyFieldHTML('👤 ' + (currentLang==='km'?'ឈ្មោះគណនី':'Account Name'), fields.login_name);
  if(fields.login_password) html += copyFieldHTML('🔑 ' + (currentLang==='km'?'លេខសម្ងាត់':'Password'), fields.login_password);
  if(fields.has_totp && fields.totp_secret){
    html += copyFieldHTML('🔐 ' + (currentLang==='km'?'Authenticator Key (ពេញ)':'Authenticator Key (full)'), fields.totp_secret);
    html += copyFieldHTML('⚡ ' + (currentLang==='km'?'លេខកូដលឿន (Live)':'Fast code (Live)'), '000 000', {big:true, refreshable:true, orderId, id:'live-'+orderId});
  }
  if(!fields.login_name && !fields.login_password && fields.delivery_note){
    html += copyFieldHTML('📦 ' + (currentLang==='km'?'ព័ត៌មានប្រគល់ជូន':'Delivery note'), fields.delivery_note);
  }
  html += `
    <div class="copy-field guide-link" onclick="event.stopPropagation(); openGuideSheet();">
      <div>
        <div class="cf-label" style="margin-bottom:2px;">📲 ${currentLang==='km'?'ជំហានទាំងអស់':'Full guide'}</div>
        <div class="cf-value">${t('how_to_login_full') || 'How to install & log in'}</div>
      </div>
      <span class="muted">›</span>
    </div>`;
  // auto-load the live code once, right after render
  if(fields.has_totp) setTimeout(() => refreshLiveField('cf-live-' + orderId, orderId), 50);
  return html;
}

/* ---------- help tab: guide sheet + song toggle ---------- */
function openGuideSheet(){
  document.getElementById('guide-sheet').classList.add('open');
  document.getElementById('backdrop').classList.add('open');
  if(tg) tg.BackButton.show();
  haptic('light');
}
let musicPlaying = false;
function toggleSong(){
  const audio = document.getElementById('bg-music');
  const btn = document.getElementById('song-toggle');
  musicPlaying = !musicPlaying;
  if(musicPlaying){ audio.play().catch(()=>{}); btn.textContent = '🔊 ' + t('song') + ' ON'; }
  else{ audio.pause(); btn.textContent = '🔈 ' + t('song') + ' OFF'; }
  haptic('light');
}

/* ---------- init ---------- */
document.addEventListener('DOMContentLoaded', () => {
  initTelegram();
  setLang('km');
  loadCatalog();
  switchTab('shop');
});
