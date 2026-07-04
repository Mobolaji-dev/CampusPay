import { getToken } from "./auth.js";

const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://campuspay.pxxl.run';

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
