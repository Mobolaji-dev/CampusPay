import { auth } from "./firebaseAuth.js";
import { onAuthStateChanged } from "https://www.gstatic.com/firebasejs/12.15.0/firebase-auth.js";

const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://campuspay-web.vercel.app';

// DOM elements
const balanceAmountEl = document.querySelector('.balance-amount');
const lockedAmountEl = document.querySelector('.status-cards .status-card:first-child .status-amount');
const accountNumberEl = document.querySelector('.account-number');
const cardTitleEl = document.querySelector('.card-title');

// Track authentication state
onAuthStateChanged(auth, async (user) => {
  if (!user) {
    console.log("No authenticated user, redirecting to login.html...");
    window.location.href = "login.html";
    return;
  }

  try {
    const token = await user.getIdToken();
    localStorage.setItem('token', token);
    localStorage.setItem('uid', user.uid);
    
    // Fetch wallet data
    await fetchWalletData(token);
  } catch (err) {
    console.error("Error refreshing token or fetching wallet data:", err);
  }
});

async function fetchWalletData(token) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/wallet`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (response.status === 401) {
      window.location.href = "login.html";
      return;
    }

    if (!response.ok) {
      throw new Error(`Failed to fetch wallet: ${response.statusText}`);
    }

    const data = await response.json();
    console.log("Wallet data fetched:", data);

    // Update UI elements
    updateUI(data);
  } catch (error) {
    console.error("Error fetching wallet data:", error);
    if (balanceAmountEl) balanceAmountEl.textContent = "Error loading";
  }
}

function updateUI(data) {
  // Format available balance (e.g. 25000 -> ₦25,000)
  if (balanceAmountEl) {
    const formattedBalance = new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: 'NGN',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2
    }).format(data.available_balance);
    balanceAmountEl.textContent = formattedBalance;
  }

  // Format locked balance
  if (lockedAmountEl) {
    const formattedLocked = new Intl.NumberFormat('en-NG', {
      style: 'currency',
      currency: 'NGN',
      minimumFractionDigits: 0,
      maximumFractionDigits: 2
    }).format(data.locked_balance || 0);
    lockedAmountEl.textContent = formattedLocked;
  }

  // Account Number
  if (accountNumberEl) {
    if (data.bank_account_number) {
      accountNumberEl.textContent = data.bank_account_number;
    } else {
      accountNumberEl.textContent = "Provisioning...";
    }
  }

  // Institutional / Bank Name
  if (cardTitleEl && data.bank_name) {
    cardTitleEl.textContent = data.bank_name;
  }
}

// Copy Account Number functionality
const copyBtn = document.querySelector('.copy-btn');
if (copyBtn && accountNumberEl) {
  copyBtn.addEventListener('click', () => {
    const accNum = accountNumberEl.textContent;
    if (accNum && accNum !== "Provisioning..." && accNum !== "None") {
      navigator.clipboard.writeText(accNum).then(() => {
        // Change icon color temporarily to show success
        const origColor = copyBtn.style.color;
        copyBtn.style.color = '#10B981'; // Green
        setTimeout(() => {
          copyBtn.style.color = origColor;
        }, 1500);
      }).catch(err => {
        console.error("Failed to copy account number:", err);
      });
    }
  });
}

// Bottom Nav Navigation
const navItems = document.querySelectorAll('.bottom-nav .nav-item');
if (navItems.length >= 4) {
  navItems[0].addEventListener('click', () => window.location.href = 'dashboard.html');
  navItems[1].addEventListener('click', () => window.location.href = 'catalogue.html');
  navItems[2].addEventListener('click', () => window.location.href = 'transactions.html');
  navItems[3].addEventListener('click', () => window.location.href = 'profile.html');
}
