import { getToken } from "./auth.js";

document.addEventListener('DOMContentLoaded', async () => {
  const token  = await getToken();
  if(!token) {
    window.location.href = "index.html"
  }

  try {
    const res = await fetch ('https://campuspay.pxxl.run/api/wallet', {
      headers: {
        "Authorization": `Bearer ${token}`
      }
    });

    if(!res.ok) throw new Error("Failed to load wallet");

    const wallet = await res.json();


    const accountName = document.getElementById("account-name");
    const availableBal = document.getElementById("available-balance");
    const lockedBal = document.getElementById("locked-balance");
    const accountNum = document.getElementById("account-number");
    const bankName = document.getElementById("bank-name");

    accountName.textContent = wallet.full_name;
    availableBal.innerHTML =  `&#8358;${parseFloat(wallet.available_balance).toLocaleString()}`;
    lockedBal.innerHTML = `&#8358;${parseFloat(wallet.locked_balance).toLocaleString()}`;
    
    if(wallet.bank_account_number) {
      accountNum.textContent = wallet.bank_account_number;
      bankName.textContent = wallet.bank_name;
    } else {
      accountNum.textContent = "Not Provisioned";
      bankName.textContent = "Not Provisioned";
    }
    
  } catch (err) {
    console.error("Dashboard error:", err)
  }
});


