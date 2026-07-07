import { getToken, API_BASE_URL } from "./auth.js";

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

function normalizeDirection(direction) {
  const normalized = String(direction || '').toLowerCase().trim();
  if (normalized === '+' || normalized === 'in' || normalized === 'credit' || normalized === 'deposit') return 'in';
  if (normalized === '-' || normalized === 'out' || normalized === 'debit' || normalized === 'withdrawal') return 'out';

  const words = normalized.match(/\b\w+\b/g) || [];
  const inKeywords = ['in', 'credit', 'deposit', 'received', 'fund', 'funding', 'income'];
  const outKeywords = ['out', 'debit', 'withdrawal', 'paid', 'payment', 'spent', 'expense', 'transfer'];

  if (words.some(word => inKeywords.includes(word))) return 'in';
  if (words.some(word => outKeywords.includes(word))) return 'out';
  return 'out';
}

function createActivityItem(tx) {
  const item = document.createElement('div');
  item.className = 'activity-item';

  const directionValue = normalizeDirection(tx.direction);

  const iconBox = document.createElement('div');
  iconBox.className = directionValue === 'in' ? 'activity-icon-box bg-gray-light' : 'activity-icon-box bg-gray';

  iconBox.innerHTML = directionValue === 'in'
    ? '<svg viewBox="0 0 24 24" fill="none" stroke="#0047FF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><polyline points="19 12 12 19 5 12"></polyline></svg>'
    : '<svg viewBox="0 0 24 24" fill="none" stroke="#374151" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="19" x2="12" y2="5"></line><polyline points="5 12 12 5 19 12"></polyline></svg>';

  const details = document.createElement('div');
  details.className = 'activity-details';

  const name = document.createElement('h4');
  name.className = 'activity-name';
  name.textContent = tx.description || 'Transaction';

  const meta = document.createElement('p');
  meta.className = 'activity-meta';
  const typeLabel = tx.type ? tx.type.charAt(0).toUpperCase() + tx.type.slice(1) : 'Transaction';
  meta.textContent = `${typeLabel} • ${formatDateTime(tx.created_at)}`;

  details.appendChild(name);
  details.appendChild(meta);

  const rawAmount = Number(String(tx.amount || '0').replace(/[^0-9.-]+/g, ''));
  const sign = directionValue === 'in' ? '+' : '-';
  const amountDiv = document.createElement('div');
  amountDiv.className = directionValue === 'in' ? 'activity-amount positive' : 'activity-amount negative';
  amountDiv.innerHTML = `${sign}${currencyFormatter.format(Math.abs(rawAmount))}`;

  item.appendChild(iconBox);
  item.appendChild(details);
  item.appendChild(amountDiv);
  return item;
}

async function loadRecentActivity(token) {
  const activityList = document.querySelector('.activity-list');
  if (!activityList) return;

  try {
    activityList.innerHTML = '<div style="padding: 24px; text-align: center; color: #6b7280; font-size: 14px;">Loading recent activity…</div>';
    const res = await fetch(`${API_BASE_URL}/api/wallet/transactions?limit=4`, {
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
      }
    });

    if (!res.ok) throw new Error("Failed to load recent activity");

    const transactions = await res.json();
    activityList.innerHTML = '';

    if (!Array.isArray(transactions) || transactions.length === 0) {
      activityList.innerHTML = '<div style="padding: 24px; text-align: center; color: #6b7280; font-size: 14px;">No recent transactions</div>';
      return;
    }

    transactions.forEach(tx => {
      activityList.appendChild(createActivityItem(tx));
    });

  } catch (err) {
    console.error("Error loading recent activity:", err);
    activityList.innerHTML = '<div style="padding: 24px; text-align: center; color: #b91c1c; font-size: 14px;">Failed to load transactions</div>';
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  const token = await getToken();
  if (!token) {
    console.log("No authenticated token, redirecting to index.html...");
    window.location.href = "index.html";
    return;
  }

  try {
    let res = await fetch(`${API_BASE_URL}/api/wallet`, {
      headers: {
        "Authorization": `Bearer ${token}`,
        "Content-Type": "application/json"
      }
    });

    if (res.status === 401) {
      window.location.href = "index.html";
      return;
    }

    // Self-healing: if the user exists in Firebase but has not been created in the database yet
    if (res.status === 404) {
      console.log("User/wallet not found in DB (404). Attempting self-healing sync...");
      const syncRes = await fetch(`${API_BASE_URL}/auth/sync`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          full_name: localStorage.getItem('displayName') || null,
          role: 'student'
        })
      });

      if (syncRes.ok) {
        console.log("Auth sync successful. Retrying wallet fetch...");
        res = await fetch(`${API_BASE_URL}/api/wallet`, {
          headers: {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
          }
        });
      }
    }

    if (!res.ok) throw new Error("Failed to load wallet");

    const wallet = await res.json();
    console.log("Wallet data fetched:", wallet);

    const accountName = document.getElementById("account-name");
    const availableBal = document.getElementById("available-balance");
    const lockedBal = document.getElementById("locked-balance");
    const accountNum = document.getElementById("account-number");
    const bankName = document.getElementById("bank-name");

    if (accountName) {
      accountName.textContent = wallet.full_name
        || localStorage.getItem('displayName')
        || localStorage.getItem('fullName')
        || "CampusPay User";
    }
    
    if (availableBal) {
      availableBal.innerHTML = `&#8358;${parseFloat(wallet.available_balance || 0).toLocaleString()}`;
    }
    
    if (lockedBal) {
      lockedBal.innerHTML = `&#8358;${parseFloat(wallet.locked_balance || 0).toLocaleString()}`;
    }
    
    if (accountNum) {
      accountNum.textContent = wallet.bank_account_number || "Not Provisioned";
    }

    if (bankName) {
      bankName.textContent = wallet.bank_name || "Not Provisioned";
    }

    // Load recent activity from transactions endpoint
    loadRecentActivity(token);
    
  } catch (err) {
    console.error("Dashboard error:", err);
  }
});

// Copy Account Number functionality
document.addEventListener('DOMContentLoaded', () => {
  const copyBtn = document.querySelector('.copy-btn');
  const accountNumEl = document.getElementById('account-number');
  if (copyBtn && accountNumEl) {
    copyBtn.addEventListener('click', () => {
      const accNum = accountNumEl.textContent;
      if (accNum && accNum !== "Not Provisioned" && accNum !== "Provisioning...") {
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
});
