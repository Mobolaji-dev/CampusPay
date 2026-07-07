import { getToken, API_BASE_URL } from './auth.js';

const currencyFormatter = new Intl.NumberFormat('en-NG', {
  style: 'currency',
  currency: 'NGN',
  minimumFractionDigits: 0,
});

function formatCurrency(amount) {
  return currencyFormatter.format(Number(amount || 0));
}

function getCheckoutItem() {
  const payload = window.sessionStorage.getItem('checkoutItem');
  if (!payload) return null;
  try {
    return JSON.parse(payload);
  } catch (error) {
    return null;
  }
}

function renderCheckout(item) {
  const productName = document.getElementById('product-name');
  const productDesc = document.getElementById('product-desc');
  const basePrice = document.getElementById('base-price');
  const totalPrice = document.getElementById('total-price');
  const orderContext = document.getElementById('order-context');

  const totalAmount = Number(item.price || 0);
  productName.textContent = item.name || 'Unknown product';
  productDesc.textContent = item.description || 'No description available.';
  basePrice.textContent = formatCurrency(item.price);
  totalPrice.textContent = formatCurrency(totalAmount);
  orderContext.textContent = `Vendor: ${item.vendor_name || item.vendor_id}`;
}

function showError(message) {
  const errorEl = document.getElementById('checkout-error');
  errorEl.textContent = message;
}

async function submitPayment(event) {
  event.preventDefault();

  const item = getCheckoutItem();
  if (!item) {
    showError('Purchase details are missing. Return to the catalogue and try again.');
    return;
  }

  const pinInput = document.getElementById('transaction-pin');
  const pin = pinInput.value.trim();
  if (pin.length !== 4 || !/^\d{4}$/.test(pin)) {
    showError('Enter a valid 4-digit PIN.');
    pinInput.focus();
    return;
  }

  const totalAmount = Number(item.price || 0);
  const payload = {
    vendor_id: item.vendor_id,
    item_description: item.name,
    item_amount: item.price,
    pin,
  };

  const button = document.getElementById('confirm-payment');
  button.disabled = true;
  button.textContent = 'Processing…';
  showError('');

  try {
    const token = await getToken();
    if (!token) {
      window.location.href = 'index.html';
      return;
    }

    const response = await fetch(`${API_BASE_URL}/api/orders`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(payload),
    });

    if (response.status === 401) {
      window.location.href = 'index.html';
      return;
    }

    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.message || 'Payment failed. Please try again.');
    }

    if (!result.order_id || !result.qr_token) {
      throw new Error('Unexpected response from server.');
    }

    const successPayload = {
      vendor_id: item.vendor_id,
      vendor_name: item.vendor_name,
      name: item.name,
      description: item.description,
      total_charged: result.total_charged ?? totalAmount,
      order_id: result.order_id,
      qr_token: result.qr_token,
      timer_expire_at: result.timer_expires_at,
      status: result.status || 'SUCCESS',
    };

    window.sessionStorage.setItem('latestOrder', JSON.stringify(successPayload));
    window.location.href = 'success.html';
  } catch (error) {
    showError(error.message || 'Unable to complete payment.');
  } finally {
    button.disabled = false;
    button.innerHTML = '<i class="fa-solid fa-lock"></i> Confirm Payment';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const item = getCheckoutItem();
  if (!item) {
    window.location.href = 'vendor.html';
    return;
  }

  renderCheckout(item);
  const form = document.getElementById('checkout-form');
  form.addEventListener('submit', submitPayment);
});
