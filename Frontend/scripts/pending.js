import { getToken } from './auth.js';

const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://campuspay.pxxl.run';

const currencyFormatter = new Intl.NumberFormat('en-NG', {
  style: 'currency',
  currency: 'NGN',
  minimumFractionDigits: 0,
});

function formatCurrency(value) {
  return currencyFormatter.format(Number(value || 0));
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || 'Unknown date';
  return new Intl.DateTimeFormat('en-GB', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function createOrderCard(order) {
  const card = document.createElement('article');
  card.className = 'order-card';

  const media = document.createElement('div');
  media.className = 'order-image';
  const img = document.createElement('img');
  img.src = order.image_url || 'https://images.unsplash.com/photo-1503342452485-86f7f2b6c5f1?auto=format&fit=crop&w=600&q=80';
  img.alt = order.name || 'Pending order image';
  media.appendChild(img);

  const content = document.createElement('div');
  content.className = 'card-content';

  const header = document.createElement('div');
  header.className = 'card-header';

  const title = document.createElement('h3');
  title.className = 'item-name';
  title.textContent = order.name || 'Untitled item';

  const price = document.createElement('span');
  price.className = 'item-price';
  price.textContent = formatCurrency(order.price);

  header.appendChild(title);
  header.appendChild(price);

  const description = document.createElement('p');
  description.className = 'item-desc';
  description.textContent = order.description || 'No description provided.';

  const metaRow = document.createElement('div');
  metaRow.className = 'meta-row';

  const location = document.createElement('span');
  location.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>${order.location || 'Unknown location'}`;

  const date = document.createElement('span');
  date.textContent = formatDate(order.created_at);

  metaRow.appendChild(location);
  metaRow.appendChild(date);

  const statusRow = document.createElement('div');
  statusRow.className = 'status-row';

  const statusBadge = document.createElement('span');
  statusBadge.className = 'status-badge';
  statusBadge.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M12 8v4l3 3"></path></svg>${order.status?.toUpperCase() || 'PENDING'}`;

  const qrToken = document.createElement('div');
  qrToken.className = 'qr-token';
  qrToken.innerHTML = `<span>QR Token</span><span>${order.qr_token || 'N/A'}</span>`;

  statusRow.appendChild(statusBadge);
  statusRow.appendChild(qrToken);

  content.appendChild(header);
  content.appendChild(description);
  content.appendChild(metaRow);
  content.appendChild(statusRow);

  card.appendChild(media);
  card.appendChild(content);
  return card;
}

function renderEmptyState(message) {
  const list = document.getElementById('pending-orders-list');
  list.innerHTML = `<div class="empty-state"><p>${message}</p></div>`;
}

function renderOrders(orders) {
  const count = document.getElementById('order-count');
  const list = document.getElementById('pending-orders-list');

  if (!Array.isArray(orders) || orders.length === 0) {
    count.textContent = 'No pending orders';
    renderEmptyState('No pending orders at this time. Check back later.');
    return;
  }

  count.textContent = `${orders.length} Pending Order${orders.length === 1 ? '' : 's'}`;
  list.innerHTML = '';
  orders.forEach(order => list.appendChild(createOrderCard(order)));
}

async function loadPendingOrders() {
  const list = document.getElementById('pending-orders-list');
  const count = document.getElementById('order-count');
  count.textContent = 'Loading…';
  list.innerHTML = '<div class="loading-state">Loading your pending orders…</div>';

  const token = await getToken();
  if (!token) {
    window.location.href = 'index.html';
    return;
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/orders/pending`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (response.status === 401) {
      window.location.href = 'index.html';
      return;
    }

    if (!response.ok) {
      throw new Error('Failed to load pending orders');
    }

    const orders = await response.json();
    renderOrders(orders);
  } catch (error) {
    console.error('Pending orders fetch failed:', error);
    count.textContent = 'Unable to load orders';
    renderEmptyState('Unable to retrieve pending orders. Please refresh or try again later.');
  }
}

document.addEventListener('DOMContentLoaded', loadPendingOrders);
