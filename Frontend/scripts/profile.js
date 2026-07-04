import { auth } from "./fireAuth.js";
import { signOut } from "https://www.gstatic.com/firebasejs/12.15.0/firebase-auth.js";

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
  } catch(err) {
    console.error(err);
  }


  const profile = await res.json();
})






// logout function

const logout = document.getElementById("logout-btn");

logout.addEventListener('click', () => {
  signOut(auth).then (()=> {
    window.location.href = 'index.html'
  }). catch((error) => {
    console.error(`Error logging out`, error)
  })
})
