const currencyFormatter = new Intl.NumberFormat('en-NG', {
  style: 'currency',
  currency: 'NGN',
  minimumFractionDigits: 0,
});

function formatCurrency(amount) {
  return currencyFormatter.format(Number(amount || 0));
}

function formatExpiry(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || 'Unknown';
  const options = { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
  return new Intl.DateTimeFormat('en-GB', options).format(date);
}

function loadReceipt() {
  const stored = window.sessionStorage.getItem('latestOrder');
  if (!stored) {
    window.location.href = 'dashboard.html';
    return;
  }

  let order;
  try {
    order = JSON.parse(stored);
  } catch {
    window.location.href = 'dashboard.html';
    return;
  }

  const qrCode = document.getElementById('qr-code');
  const receiptItem = document.getElementById('receipt-item');
  const receiptVendor = document.getElementById('receipt-vendor');
  const receiptVendorName = document.getElementById('receipt-vendor-name');
  const receiptAmount = document.getElementById('receipt-amount');
  const receiptExpiry = document.getElementById('receipt-expiry');
  const receiptOrder = document.getElementById('receipt-order');
  const receiptStatus = document.getElementById('receipt-status');

  receiptItem.textContent = order.name || 'Purchased item';
  receiptVendor.textContent = order.vendor_id || 'Unknown vendor';
  receiptVendorName.textContent = order.vendor_name || 'Unknown vendor';
  receiptAmount.textContent = formatCurrency(order.total_charged);
  receiptExpiry.textContent = formatExpiry(order.timer_expire_at);
  receiptOrder.textContent = order.order_id || 'N/A';
  receiptStatus.textContent = order.status ? order.status.toUpperCase() : 'SUCCESS';

  const qrData = encodeURIComponent(order.qr_token || order.order_id || '');
  qrCode.src = `https://api.qrserver.com/v1/create-qr-code/?size=400x400&margin=10&data=${qrData}`;}

document.addEventListener('DOMContentLoaded', () => {
  const cancelButton = document.getElementById('cancel-button');
  cancelButton.addEventListener('click', () => {
    window.location.href = 'dashboard.html';
  });
  loadReceipt();
});
