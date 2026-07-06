import { getToken } from "./auth.js";

const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://campuspay.pxxl.run';

const currencyFormatter = new Intl.NumberFormat('en-NG', {
  style: 'currency',
  currency: 'NGN',
  minimumFractionDigits: 0,
});

function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const options = {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  };
  return new Intl.DateTimeFormat('en-GB', options).format(date);
}

function getStatusClass(status) {
  const normalized = String(status).toLowerCase();
  if (normalized.includes('complete') || normalized.includes('success')) return 'status-completed';
  if (normalized.includes('pending')) return 'status-pending';
  if (normalized.includes('process')) return 'status-processing';
  if (normalized.includes('fail') || normalized.includes('decline') || normalized.includes('cancel')) return 'status-failed';
  return 'status-pending';
}

function normalizeDirection(direction) {
  const normalized = String(direction || '').toLowerCase().trim();
  const words = normalized.match(/\b\w+\b/g) || [];
  const inKeywords = ['in', 'credit', 'deposit', 'received', 'fund', 'funding', 'income'];
  const outKeywords = ['out', 'debit', 'withdrawal', 'paid', 'payment', 'spent', 'expense', 'transfer'];

  if (words.some(word => inKeywords.includes(word))) return 'in';
  if (words.some(word => outKeywords.includes(word))) return 'out';
  return 'out';
}

function getDirectionClass(direction) {
  return direction === 'in' ? 'positive' : 'negative';
}

function getIconClasses(direction) {
  return direction === 'in' ? 'bg-green-light' : 'bg-blue-light';
}

function createTransactionCard(item) {
  const wrapper = document.createElement('article');
  wrapper.className = 'transaction-card';

  const iconBox = document.createElement('div');
  const directionValue = normalizeDirection(item.direction);
  iconBox.className = `icon-box ${getIconClasses(directionValue)}`;
  iconBox.innerHTML = directionValue === 'in'
    ? '<i class="fa-solid fa-arrow-down-left" aria-hidden="true"></i>'
    : '<i class="fa-solid fa-arrow-up-right" aria-hidden="true"></i>';

  const details = document.createElement('div');
  details.className = 'card-details';

  const title = document.createElement('h3');
  title.className = 'item-title';
  title.textContent = item.description || 'Unknown transaction';
  details.appendChild(title);

  const category = document.createElement('p');
  category.className = 'item-category';
  const typeLabel = item.type ? item.type : 'Transaction';
  category.textContent = `${typeLabel} · ${formatDateTime(item.created_at)}`;
  details.appendChild(category);

  const amounts = document.createElement('div');
  amounts.className = 'card-amounts';

  const amount = document.createElement('p');
  const direction = normalizeDirection(item.direction);
  const rawAmount = Number(String(item.amount || '0').replace(/[^0-9.-]+/g, ''));
  const sign = direction === 'in' ? '+' : '-';
  amount.className = `amount ${getDirectionClass(direction)}`;
  amount.textContent = `${sign}${currencyFormatter.format(Math.abs(rawAmount))}`;
  amounts.appendChild(amount);

  const status = document.createElement('span');
  status.className = `status-pill ${getStatusClass(item.status)}`;
  status.textContent = String(item.status || 'Unknown').toUpperCase();
  amounts.appendChild(status);

  wrapper.appendChild(iconBox);
  wrapper.appendChild(details);
  wrapper.appendChild(amounts);
  return wrapper;
}

function renderEmptyState(message) {
  const list = document.getElementById('transaction-list');
  list.innerHTML = `
    <div class="empty-state">
      <p class="empty-title">${message}</p>
      <p class="empty-subtitle">If you expected activity, try refreshing the page.</p>
    </div>
  `;
}

function updateFilterTabs(transactions) {
  const tabs = document.querySelectorAll('.filter-tabs .tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(button => {
        button.classList.toggle('active', button === tab);
        button.setAttribute('aria-selected', button === tab ? 'true' : 'false');
      });
      const filter = tab.getAttribute('data-filter');
      renderTransactions(transactions, filter);
    });
  });
}

function renderTransactions(transactions, filter = 'all') {
  const list = document.getElementById('transaction-list');
  const filtered = transactions.filter(item => {
    if (filter === 'all') return true;
    return normalizeDirection(item.direction) === filter;
  });

  if (!filtered.length) {
    renderEmptyState('No transactions found');
    return;
  }

  list.innerHTML = '';
  filtered.forEach(item => list.appendChild(createTransactionCard(item)));
}

async function loadTransactions() {
  const list = document.getElementById('transaction-list');
  const token = await getToken();
  if (!token) {
    window.location.href = 'index.html';
    return;
  }

  renderEmptyState('Loading your transaction history…');

  try {
    const response = await fetch(`${API_BASE_URL}/api/wallet/transactions`, {
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
      throw new Error('Unable to fetch transactions');
    }

    const transactions = await response.json();
    if (!Array.isArray(transactions) || transactions.length === 0) {
      renderEmptyState('No transactions found');
      return;
    }

    updateFilterTabs(transactions);
    renderTransactions(transactions, 'all');
  } catch (error) {
    console.error('Transaction fetch failed:', error);
    renderEmptyState('Failed to load transactions');
  }
}

window.addEventListener('DOMContentLoaded', loadTransactions);
