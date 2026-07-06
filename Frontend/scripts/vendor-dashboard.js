import { getToken } from './auth.js';

const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://campuspay.pxxl.run';

// ── State ────────────────────────────────────────────────────────────────────
let currentOrderId = null;
let html5QrCode = null;
let scannerActive = false;
let refreshInterval = null;

// ── DOM refs ─────────────────────────────────────────────────────────────────
const ordersList     = document.getElementById('orders-list');
const orderCount     = document.getElementById('order-count');
const qrModal        = document.getElementById('qr-modal');
const qrReader       = document.getElementById('qr-reader');
const closeModalBtn  = document.getElementById('close-modal-btn');
const scanStatus     = document.getElementById('scan-status');
const manualInput    = document.getElementById('manual-token-input');
const manualSubmit   = document.getElementById('manual-submit-btn');
const refreshBtn     = document.getElementById('refresh-btn');
const vendorNameTag  = document.getElementById('vendor-name-tag');
const toast          = document.getElementById('toast');

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  // Guard: redirect if not logged in
  const token = await getToken();
  if (!token) {
    window.location.href = 'index.html';
    return;
  }

  // Guard: redirect students
  const role = localStorage.getItem('role');
  if (role && role !== 'Vendor') {
    window.location.href = 'dashboard.html';
    return;
  }

  // Show vendor name
  const vName = localStorage.getItem('vendorName') || localStorage.getItem('fullName') || '';
  if (vName) vendorNameTag.textContent = vName;

  // Cache bank account status for post-scan nudge (fire-and-forget)
  cacheVendorBankStatus(token);

  await loadPendingOrders();

  // Auto-refresh every 30s
  refreshInterval = setInterval(loadPendingOrders, 30_000);

  // Manual refresh button
  refreshBtn.addEventListener('click', () => {
    refreshBtn.classList.add('spinning');
    loadPendingOrders().finally(() => refreshBtn.classList.remove('spinning'));
  });

  // Modal close
  closeModalBtn.addEventListener('click', closeScanner);
  qrModal.addEventListener('click', (e) => {
    if (e.target === qrModal) closeScanner();
  });

  // Manual token submit
  manualSubmit.addEventListener('click', () => {
    const token = manualInput.value.trim();
    if (token) handleScan(token);
  });

  manualInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const t = manualInput.value.trim();
      if (t) handleScan(t);
    }
  });
});

// ── Cache vendor bank status ──────────────────────────────────────────────────
async function cacheVendorBankStatus(token) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/profile`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    if (res.ok) {
      const profile = await res.json();
      localStorage.setItem(
        'vendorHasBankAccount',
        !!(profile.vendor_bank_account && profile.vendor_bank_code) ? 'true' : 'false'
      );
    }
  } catch { /* non-critical */ }
}

// ── Load Orders ───────────────────────────────────────────────────────────────
async function loadPendingOrders() {
  orderCount.textContent = 'Loading…';
  ordersList.innerHTML = '<div class="loading-state">Loading orders…</div>';

  const token = await getToken();
  if (!token) {
    window.location.href = 'index.html';
    return;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/api/orders/vendor/pending`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (res.status === 401) {
      window.location.href = 'index.html';
      return;
    }
    if (res.status === 403) {
      window.location.href = 'dashboard.html';
      return;
    }
    if (!res.ok) throw new Error('Failed to load orders');

    const orders = await res.json();
    renderOrders(orders);
  } catch (err) {
    console.error('Failed to load vendor orders:', err);
    orderCount.textContent = 'Error';
    ordersList.innerHTML = `<div class="empty-state">
      <div class="empty-state-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
      <p>Unable to load orders. Pull to refresh.</p>
    </div>`;
  }
}

// ── Render ────────────────────────────────────────────────────────────────────
function renderOrders(orders) {
  if (!Array.isArray(orders) || orders.length === 0) {
    orderCount.textContent = '0 Pending';
    ordersList.innerHTML = `<div class="empty-state">
      <div class="empty-state-icon">🎉</div>
      <p>No pending orders right now.</p>
    </div>`;
    return;
  }

  orderCount.textContent = `${orders.length} Pending`;
  ordersList.innerHTML = '';
  orders.forEach(order => ordersList.appendChild(createOrderCard(order)));
}

function formatTime(isoStr) {
  const d = new Date(isoStr);
  if (isNaN(d.getTime())) return isoStr;
  return new Intl.DateTimeFormat('en-NG', {
    hour: '2-digit', minute: '2-digit', hour12: true,
    month: 'short', day: 'numeric',
  }).format(d);
}

function formatMoney(val) {
  return '₦' + Number(val).toLocaleString('en-NG', { minimumFractionDigits: 2 });
}

function createOrderCard(order) {
  const card = document.createElement('div');
  card.className = 'order-card';
  card.dataset.orderId = order.order_id;

  card.innerHTML = `
    <div class="order-card-header">
      <h3 class="order-item-name">${escHtml(order.item_description)}</h3>
      <span class="order-amount">${formatMoney(order.item_amount)}</span>
    </div>
    <div class="order-meta">
      <div class="meta-line">
        <i class="fa-solid fa-user"></i>
        <span>Buyer: <strong>${escHtml(order.student_name)}</strong></span>
      </div>
      <div class="meta-line">
        <i class="fa-regular fa-clock"></i>
        <span>${formatTime(order.created_at)}</span>
      </div>
    </div>
    <div class="status-pill">
      <i class="fa-solid fa-hourglass-half"></i>
      Awaiting Pickup
    </div>
    <button class="verify-btn" data-order-id="${escAttr(order.order_id)}">
      <i class="fa-solid fa-qrcode"></i>
      Verify Payment
    </button>
  `;

  card.querySelector('.verify-btn').addEventListener('click', () => {
    openScanner(order.order_id);
  });

  return card;
}

function escHtml(str) {
  return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escAttr(str) {
  return String(str || '').replace(/"/g,'&quot;');
}

// ── Scanner ───────────────────────────────────────────────────────────────────
function openScanner(orderId) {
  currentOrderId = orderId;
  manualInput.value = '';
  scanStatus.className = 'scan-status hidden';
  scanStatus.textContent = '';
  qrModal.classList.add('open');

  // Start html5-qrcode
  html5QrCode = new Html5Qrcode('qr-reader');
  Html5Qrcode.getCameras()
    .then(cameras => {
      if (!cameras || cameras.length === 0) return; // fallback only
      const cameraId = cameras[cameras.length - 1].id; // prefer back camera
      html5QrCode.start(
        cameraId,
        { fps: 10, qrbox: { width: 220, height: 220 } },
        (decodedText) => {
          if (!scannerActive) return;
          scannerActive = false;
          stopCamera();
          handleScan(decodedText);
        },
        () => {} // ignore scan errors (frame by frame noise)
      ).then(() => { scannerActive = true; })
       .catch(() => {
         // Camera failed — user must use fallback
         showScanStatus('Camera unavailable. Use the manual input below.', 'error');
       });
    })
    .catch(() => {
      showScanStatus('Camera permission denied. Use the manual input below.', 'error');
    });
}

function stopCamera() {
  if (html5QrCode) {
    html5QrCode.stop().catch(() => {});
    html5QrCode = null;
  }
  scannerActive = false;
}

function closeScanner() {
  stopCamera();
  qrModal.classList.remove('open');
  currentOrderId = null;
  // Clear the QR reader DOM so it re-initialises cleanly next time
  qrReader.innerHTML = '';
}

// ── handleScan ─────────────────────────────────────────────────────────────────
async function handleScan(scannedToken) {
  // 1. Decode JWT payload to extract order_id
  let orderId;
  try {
    const base64 = scannedToken.split('.')[1];
    const decoded = JSON.parse(atob(base64.replace(/-/g, '+').replace(/_/g, '/')));
    orderId = decoded.order_id;
    if (!orderId) throw new Error('No order_id in token');
  } catch {
    showScanStatus('Invalid QR code format.', 'error');
    showToast('Invalid QR code format.', 'error');
    return;
  }

  showScanStatus('Verifying payment…', '');

  const token = await getToken();
  try {
    const res = await fetch(`${API_BASE_URL}/api/orders/${orderId}/scan`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ qr_token: scannedToken }),
    });

    const result = await res.json();

    if (res.ok) {
      const amount = formatMoney(result.amount_paid_to_vendor);
      const hasBankAccount = localStorage.getItem('vendorHasBankAccount') === 'true';
      if (hasBankAccount) {
        showScanStatus(`✓ Payment verified! ${amount} sent to your account.`, 'success');
        showToast(`Payment verified! ${amount} sent to your account.`, 'success');
      } else {
        showScanStatus(`✓ Order confirmed! Set up your bank account in Profile to receive ${amount}.`, 'success');
        showToast('Order confirmed! Go to Profile → set bank account to receive funds.', 'error');
      }
      setTimeout(() => {
        closeScanner();
        loadPendingOrders();
      }, 2500);
    } else {
      const msg = getScanErrorMessage(res.status, result.detail);
      showScanStatus(msg, 'error');
      showToast(msg, 'error');
    }
  } catch (err) {
    console.error('Scan request failed:', err);
    showScanStatus('Network error — please retry.', 'error');
    showToast('Network error — please retry.', 'error');
  }
}

function getScanErrorMessage(status, detail) {
  const map = {
    401: 'QR code has expired.',
    403: 'This QR code is not for your store.',
    404: 'Order not found.',
    409: 'Order already confirmed or expired.',
    500: 'Server error — please retry.',
  };
  return map[status] || detail || 'Verification failed.';
}

// ── UI Helpers ────────────────────────────────────────────────────────────────
function showScanStatus(msg, type) {
  scanStatus.textContent = msg;
  scanStatus.className = `scan-status ${type}`;
}

let toastTimer = null;
function showToast(msg, type = '') {
  toast.textContent = msg;
  toast.className = `toast show ${type ? type + '-toast' : ''}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.className = 'toast hidden';
  }, 4000);
}
