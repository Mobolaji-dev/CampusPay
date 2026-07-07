import { auth } from './firebaseAuth.js';
import { getToken } from './auth.js';
import { signOut } from 'https://www.gstatic.com/firebasejs/12.15.0/firebase-auth.js';


const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : window.location.hostname === 'campuspay-3f39.onrender.com'
  ? 'https://campuspay-3f39.onrender.com'
  : 'https://campuspay.pxxl.run';


// ── State ─────────────────────────────────────────────────────────────────────
let allBanks = [];          // [{name, code}] from Nomba
let selectedBankCode = '';
let selectedBankName = '';
let resolvedAccountName = '';
let dropdownOpen = false;

// ── DOM refs ─────────────────────────────────────────────────────────────────
const vendorNameTag       = document.getElementById('vendor-name-tag');
const avatarInitials      = document.getElementById('avatar-initials');
const profileName         = document.getElementById('profile-name');
const profileEmail        = document.getElementById('profile-email');
const accountStatusBadge  = document.getElementById('account-status-badge');
const currentAccountDisp  = document.getElementById('current-account-display');
const noAccountHint       = document.getElementById('no-account-hint');
const displayBankName     = document.getElementById('display-bank-name');
const displayAcctNumber   = document.getElementById('display-account-number');
const displayAcctName     = document.getElementById('display-account-name');
const formSectionTitle    = document.getElementById('form-section-title');

const bankSearch          = document.getElementById('bank-search');
const bankDropdown        = document.getElementById('bank-dropdown');
const bankSelectWrapper   = bankSearch.closest('.bank-select-wrapper');
const selectedBankCodeEl  = document.getElementById('selected-bank-code');
const selectedBankNameEl  = document.getElementById('selected-bank-name');

const accountNumberInput  = document.getElementById('account-number');
const verifyBtn           = document.getElementById('verify-btn');
const accountNameGroup    = document.getElementById('account-name-group');
const resolvedNameEl      = document.getElementById('resolved-account-name');

const formError           = document.getElementById('form-error');
const bankForm            = document.getElementById('bank-form');
const saveBtn             = document.getElementById('save-btn');

const logoutBtn           = document.getElementById('logout-btn');
const toast               = document.getElementById('toast');

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  const token = await getToken();
  if (!token) { window.location.href = 'index.html'; return; }

  const role = localStorage.getItem('role');
  if (role && role !== 'Vendor') { window.location.href = 'dashboard.html'; return; }

  const vName = localStorage.getItem('vendorName') || localStorage.getItem('fullName') || '';
  if (vName) vendorNameTag.textContent = vName;

  await Promise.all([loadProfile(token), loadBanks(token)]);
  bindEvents();
});

// ── Load Profile ──────────────────────────────────────────────────────────────
async function loadProfile(token) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/profile`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.status === 401) { window.location.href = 'index.html'; return; }
    if (!res.ok) return;

    const p = await res.json();

    profileName.textContent = p.full_name || '—';
    profileEmail.textContent = p.email || '—';

    // Avatar initials
    const initials = (p.full_name || 'V')
      .split(' ')
      .map(w => w[0])
      .slice(0, 2)
      .join('')
      .toUpperCase();
    avatarInitials.textContent = initials;

    renderAccountStatus(p);
  } catch (err) {
    console.error('Failed to load profile', err);
  }
}

function renderAccountStatus(profile) {
  if (profile.vendor_bank_account && profile.vendor_bank_code) {
    accountStatusBadge.textContent = 'Set';
    accountStatusBadge.className = 'status-badge is-set';
    noAccountHint.classList.add('hidden');
    currentAccountDisp.classList.remove('hidden');

    displayBankName.textContent = profile.vendor_bank_name || profile.vendor_bank_code;
    // Mask: show last 4 digits
    const acct = profile.vendor_bank_account;
    displayAcctNumber.textContent = '•'.repeat(acct.length - 4) + acct.slice(-4);
    // We don't store account name in profile response; show a placeholder
    displayAcctName.textContent = 'Saved';

    formSectionTitle.textContent = 'Update Bank Account';

    // Pre-fill form fields
    accountNumberInput.value = profile.vendor_bank_account;
    selectedBankCode = profile.vendor_bank_code;
    selectedBankName = profile.vendor_bank_name || '';
    selectedBankCodeEl.value = selectedBankCode;
    selectedBankNameEl.value = selectedBankName;
    bankSearch.value = profile.vendor_bank_name || profile.vendor_bank_code;
  } else {
    accountStatusBadge.textContent = 'Not Set';
    accountStatusBadge.className = 'status-badge not-set';
    currentAccountDisp.classList.add('hidden');
    noAccountHint.classList.remove('hidden');
  }
}

// ── Load Banks ────────────────────────────────────────────────────────────────
async function loadBanks(token) {
  try {
    const res = await fetch(`${API_BASE_URL}/api/profile/banks`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    allBanks = await res.json(); // [{name, code}]
  } catch (err) {
    console.error('Failed to load bank list', err);
    showToast('Could not load bank list. Please refresh.', 'error');
  }
}

// ── Bank Dropdown ─────────────────────────────────────────────────────────────
function openDropdown() {
  dropdownOpen = true;
  bankSelectWrapper.classList.add('open');
  renderDropdown(bankSearch.value);
  bankDropdown.classList.remove('hidden');
}

function closeDropdown() {
  dropdownOpen = false;
  bankSelectWrapper.classList.remove('open');
  bankDropdown.classList.add('hidden');
}

function renderDropdown(query) {
  const q = query.trim().toLowerCase();
  const matches = q
    ? allBanks.filter(b => b.name.toLowerCase().includes(q))
    : allBanks;

  if (matches.length === 0) {
    bankDropdown.innerHTML = '<div class="bank-empty">No banks found</div>';
    return;
  }

  bankDropdown.innerHTML = matches
    .map(b => `<div class="bank-option" data-code="${escAttr(b.code)}" data-name="${escAttr(b.name)}">${escHtml(b.name)}</div>`)
    .join('');

  bankDropdown.querySelectorAll('.bank-option').forEach(el => {
    el.addEventListener('mousedown', (e) => {
      e.preventDefault(); // prevent blur before click
      selectBank(el.dataset.code, el.dataset.name);
    });
  });
}

function selectBank(code, name) {
  selectedBankCode = code;
  selectedBankName = name;
  selectedBankCodeEl.value = code;
  selectedBankNameEl.value = name;
  bankSearch.value = name;
  closeDropdown();
  // Reset downstream state
  clearResolvedName();
  updateVerifyBtnState();
}

function clearResolvedName() {
  resolvedAccountName = '';
  resolvedNameEl.textContent = '—';
  accountNameGroup.classList.add('hidden');
  saveBtn.disabled = true;
}

function updateVerifyBtnState() {
  const acct = accountNumberInput.value.trim();
  verifyBtn.disabled = !(acct.length === 10 && selectedBankCode);
}

// ── Events ────────────────────────────────────────────────────────────────────
function bindEvents() {
  // Bank search input
  bankSearch.addEventListener('focus', openDropdown);
  bankSearch.addEventListener('blur', () => setTimeout(closeDropdown, 150));
  bankSearch.addEventListener('input', () => {
    // If user clears a previously selected bank
    if (bankSearch.value !== selectedBankName) {
      selectedBankCode = '';
      selectedBankName = '';
      selectedBankCodeEl.value = '';
      selectedBankNameEl.value = '';
      clearResolvedName();
    }
    if (!dropdownOpen) openDropdown();
    renderDropdown(bankSearch.value);
    updateVerifyBtnState();
  });

  // Account number
  accountNumberInput.addEventListener('input', () => {
    // Only allow digits
    accountNumberInput.value = accountNumberInput.value.replace(/\D/g, '').slice(0, 10);
    clearResolvedName();
    updateVerifyBtnState();
  });

  // Verify button
  verifyBtn.addEventListener('click', verifyAccount);

  // Form submit
  bankForm.addEventListener('submit', saveAccount);

  // Logout
  logoutBtn.addEventListener('click', () => {
    signOut(auth)
      .then(() => { window.location.href = 'index.html'; })
      .catch(err => console.error('Logout error', err));
  });
}

// ── Verify Account ────────────────────────────────────────────────────────────
async function verifyAccount() {
  const acct = accountNumberInput.value.trim();
  if (!acct || !selectedBankCode) return;

  setLoading(verifyBtn, true);
  hideError();
  clearResolvedName();

  try {
    const token = await getToken();
    const res = await fetch(`${API_BASE_URL}/api/profile/banks/lookup`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ account_number: acct, bank_code: selectedBankCode }),
    });

    const data = await res.json();

    if (!res.ok) {
      showError(data.detail || 'Could not verify account. Check the number and bank.');
      return;
    }

    resolvedAccountName = data.account_name;
    resolvedNameEl.textContent = resolvedAccountName;
    accountNameGroup.classList.remove('hidden');
    saveBtn.disabled = false;
    showToast('Account verified!', 'success');
  } catch (err) {
    console.error('Account verify error', err);
    showError('Network error — please try again.');
  } finally {
    setLoading(verifyBtn, false);
  }
}

// ── Save Account ──────────────────────────────────────────────────────────────
async function saveAccount(e) {
  e.preventDefault();
  if (!resolvedAccountName || !selectedBankCode) return;

  const acct = accountNumberInput.value.trim();
  setLoading(saveBtn, true);
  hideError();

  try {
    const token = await getToken();
    const res = await fetch(`${API_BASE_URL}/api/profile/vendor-bank`, {
      method: 'PATCH',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        account_number: acct,
        bank_code: selectedBankCode,
        account_name: resolvedAccountName,
        bank_name: selectedBankName,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      showError(data.detail || 'Failed to save account. Please try again.');
      return;
    }

    showToast('Bank account saved successfully!', 'success');

    // Refresh profile display
    const token2 = await getToken();
    await loadProfile(token2);
  } catch (err) {
    console.error('Save account error', err);
    showError('Network error — please try again.');
  } finally {
    setLoading(saveBtn, false);
  }
}

// ── UI Helpers ────────────────────────────────────────────────────────────────
function setLoading(btn, state) {
  btn.classList.toggle('loading', state);
  btn.disabled = state;
}

function showError(msg) {
  formError.textContent = msg;
  formError.classList.remove('hidden');
}

function hideError() {
  formError.classList.add('hidden');
}

let toastTimer = null;
function showToast(msg, type = '') {
  toast.textContent = msg;
  toast.className = `toast show${type ? ' ' + type + '-toast' : ''}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.className = 'toast hidden'; }, 4000);
}

function escHtml(str) {
  return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function escAttr(str) {
  return String(str || '').replace(/"/g, '&quot;');
}
